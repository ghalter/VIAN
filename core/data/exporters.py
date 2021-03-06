"""
Contains all Export Classes and Export Functions of VIAN
"""

import cv2
import numpy as np
import pandas as pd
from core.data.enums import ScreenshotNamingConventionOptions, get_enum_value, ImageType, TargetContainerType
from core.data.interfaces import IConcurrentJob
from core.data.computation import *
from core.container.project import *
import os
import csv
import shutil

from core.data.csv_helper import CSVFile


DEFAULT_NAMING_SCREENSHOTS = [
    ScreenshotNamingConventionOptions.Scene_ID.name,
    ScreenshotNamingConventionOptions.Shot_ID_Segment.name,
    ScreenshotNamingConventionOptions.Movie_ID.name,
    ScreenshotNamingConventionOptions.Movie_Name.name,
    ScreenshotNamingConventionOptions.Movie_Year.name,
    ScreenshotNamingConventionOptions.Movie_Source.name,
        ]


def zip_project(output_file, project_folder):
    shutil.make_archive(output_file, 'zip', project_folder)


def get_keyword_columns(project:VIANProject, container_type = None):
    keywords = dict()
    for e in project.experiments:
        for kwd in e.get_unique_keywords(container_type):
            keywords[kwd.get_full_name()] = kwd
    return keywords


class ExportDevice:
    def export(self, project, path):
        pass


class _ScreenshotExporter(ExportDevice):
    """
    A Class that is able to export Screenshots from a Project
    """
    def __init__(self, naming, annotation_visibility = None,
                 image_type = ImageType.JPG, quality = 100, smooth = False):
        self.naming = naming
        self.smooth = smooth
        self.quality = quality
        self.image_type = image_type,
        self.annotation_visibility = annotation_visibility,

    def export(self, project, path):
        for s in project.screenshots:
            if self.naming is None:
                name = build_file_name(DEFAULT_NAMING_SCREENSHOTS, s, project.movie_descriptor)
            else:
                name = build_file_name(self.naming, s, project.movie_descriptor)
            file_name = os.path.join(path, name)

            if self.annotation_visibility is None:
                annotation_visibility = s.annotation_is_visible

            if self.annotation_visibility:
                img = s.img_blend
            else:
                img = s.get_img_movie_orig_size()

            if self.smooth:
                img = cv2.GaussianBlur(img, (3, 3), 0)
            # Export depending on the image Type selected

            if self.image_type == ImageType.JPG:
                cv2.imwrite(file_name + ".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, self.quality])

            if self.image_type == ImageType.PNG:
                compression = int(np.clip(float(100 - self.quality) / 10,0,9))
                cv2.imwrite(file_name + ".png", img, [cv2.IMWRITE_PNG_COMPRESSION, compression])


    def build_file_name(self, naming, screenshot, movie_descriptor):
        """
        Generates a Filename for the Screenshots by a given naming convention

        :param naming:
        :param screenshot:
        :param movie_descriptor:
        :return:
        """
        file_name = "/"

        for i, name in enumerate(naming):
            if name is not ScreenshotNamingConventionOptions.empty.name:
                value = get_enum_value(ScreenshotNamingConventionOptions, name)
                object_type = value[0]
                object_attr = value[1]

                if object_type == "Screenshot":
                    if object_attr == "screenshot_group":
                        file_name = file_name[:-1]
                    file_name += str(getattr(screenshot, object_attr))

                if object_type == "Movie":
                    file_name += str(getattr(movie_descriptor, object_attr))

                if i < len(naming) - 1:
                    if get_enum_value(ScreenshotNamingConventionOptions, naming[i + 1])[1] == 0:
                        break
                    else:
                        file_name += "_"

        file_name = file_name.replace("__", "")
        file_name = file_name.replace("All Shots_", "_")

        return file_name


class ScreenshotsExporter():
    """
    A Class that is able to export Screenshots from a Project
    """
    def __init__(self, settings, project, naming):
        self.settings = settings
        self.project = project
        self.naming = naming

    def export(self, screenshots, dir, annotation_visibility = None, image_type = ImageType.JPG, quality = 100, smooth = False, apply_letterbox=False):
        lbox = None
        if apply_letterbox is True:
            lbox = self.project.movie_descriptor.get_letterbox_rect()
            if lbox is None:
                QMessageBox.warning(None, "No letterbox applied", "No letterbox has been applied, the default frame is used. To set a letterbox, go to Player/Set Letterbox prior to export.")
        for s in screenshots:
            if self.naming is None:
                name = build_file_name(self.settings.SCREENSHOTS_EXPORT_NAMING, s, self.project.movie_descriptor)
            else:
                name = build_file_name(self.naming, s, self.project.movie_descriptor)
            file_name = dir + name

            if annotation_visibility is None:
                annotation_visibility = s.annotation_is_visible

            if annotation_visibility:
                img = s.img_blend
            else:
                img = s.get_img_movie_orig_size()

            if smooth:
                img = cv2.GaussianBlur(img, (3, 3), 0)
            # Export depending on the image Type selected

            if lbox is not None:
                img = img[lbox[1]:lbox[1] + lbox[3], lbox[0]:lbox[0] + lbox[2]]
            if image_type.value == ImageType.JPG.value:
                cv2.imwrite(file_name + ".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])

            if image_type.value == ImageType.PNG.value:
                compression = int(np.clip(float(100 - quality) / 10,0,9))
                cv2.imwrite(file_name + ".png", img, [cv2.IMWRITE_PNG_COMPRESSION, compression])


class SegmentationExporter(ExportDevice):
    """
    A Class that is able to export a Segmentation into CSV
    """
    def __init__(self, file_path, export_ms, export_formated, export_formated_ms, export_formated_frame,
                 export_text, export_frame, t_start, t_end, t_duration, fps, segmentations):
        self.file_path = file_path
        self.fps = fps
        self.export_formated = export_formated
        self.export_formated_ms = export_formated_ms
        self.export_formated_frame = export_formated_frame
        self.export_text = export_text
        self.export_frame = export_frame
        self.t_start = t_start
        self.t_end = t_end
        self.t_duration = t_duration
        self.export_ms = export_ms
        self.segmentations = segmentations

    def export(self, project:VIANProject, path):

        def add(d, k, v):
            if k not in d:
                d[k] = []
            d[k].append(v)

        result = dict()

        if self.segmentations is None:
            self.segmentations = project.segmentation

        # Make sure we have all bodies in the header
        bodies = set()
        for segmentation in self.segmentations:
            for s in segmentation.segments:
                for a in s.get_annotations():
                    bodies.add("annotation_{}".format(a.name))
        print("All bodies", bodies)

        for segmentation in self.segmentations:
            for s in segmentation.segments: # type:Segment
                bodies_added = set()
                add(result, "segment_id", s.ID)
                add(result, "segmentation_name", segmentation.name)
                if self.export_ms:

                    if self.t_start:
                        add(result, "start_ms", s.start)

                    if self.t_end:
                        add(result, "end_ms", s.end)

                    if self.t_duration:
                        add(result, "duration_ms", s.duration)

                if self.export_formated:
                    if self.t_start:
                        add(result, "start_ts", ms_to_string(s.start))

                    if self.t_end:
                        add(result, "end_ts", ms_to_string(s.end))

                    if self.t_duration:
                        add(result, "duration_ts", ms_to_string(s.duration))

                elif self.export_formated_ms:
                    if self.t_start:
                        add(result, "start_ts", ms_to_string(s.start, include_ms=True))

                    if self.t_end:
                        add(result, "end_ts", ms_to_string(s.end, include_ms=True))

                    if self.t_duration:
                        add(result, "duration_ts", ms_to_string(s.duration, include_ms=True))

                elif self.export_formated_frame:
                    if self.t_start:
                        add(result, "start_ts", ms_to_string(s.start, include_frame=True))

                    if self.t_end:
                        add(result, "end_ts", ms_to_string(s.end, include_frame=True))

                    if self.t_duration:
                        add(result, "duration_ts", ms_to_string(s.duration, include_frame=True))

                if self.export_frame:
                    if self.t_start:
                        add(result, "start_frame", ms_to_frames(s.start, self.fps))

                    if self.t_end:
                        add(result, "end_frame", ms_to_frames(s.end, self.fps))

                    if self.t_duration:
                        add(result, "duration_frame", ms_to_frames(s.duration, self.fps))

                for b in s.get_annotations():  # type: AnnotationBody
                    column = "annotation_{}".format(b.name)
                    bodies_added.add(column)
                    add(result, column, b.content)

                for b in bodies.difference(bodies_added):
                    add(result, b, "")

        if ".xlsx" in path:
            pd.DataFrame(result).to_excel(path)
        else:
            pd.DataFrame(result).to_csv(path)


class JsonExporter():
    def segment2json(self, segment):
        pass
        # result = ""


class CSVExporter(ExportDevice):
    def __init__(self, export_segmentations = True, export_screenshots=True, export_annotations=True,
                 export_keywords = True, timestamp_format = "ms"):
        self.export_segm = export_segmentations
        self.export_ann = export_annotations
        self.export_scr = export_screenshots
        self.export_keywords = export_keywords

    def export(self, project, path):
        f = CSVFile()

        headers = ["ROW", "ID", "START_MS", "END_MS",
                   "SELECTOR_TYPE", "ANNOTATION_MIME_TYPE", "ANNOTATION_BODY_ID", "ANNOTATION_BODY",
                   "NOTES"]

        if self.export_keywords:
            keyword_mapping = get_keyword_columns(project)
            keyword_columns = keyword_mapping.keys()
            headers.extend(keyword_columns)

        f.set_header(headers)

        c = 0
        if self.export_segm:
            segments = []
            [segments.extend(s.segments) for s in project.segmentation]

            for segm in segments:  #type:Segment
                bodies = segm.get_annotations()
                if len(bodies) == 0:
                    bodies = [AnnotationBody()]
                for bd in bodies:
                    r = dict(
                        ROW = c,
                        ID = segm.unique_id,
                        START_MS = segm.get_start(),
                        END_MS = segm.get_end(),
                        SELECTOR_TYPE = "SEGMENT",
                        ANNOTATION_MIME_TYPE = bd.mime_type,
                        ANNOTATION_BODY_ID = bd.unique_id,
                        ANNOTATION_BODY = bd.content,
                        NOTES = segm.notes
                    )

                    if self.export_keywords:
                        for k in keyword_columns:
                            r[k] = 0
                        for k in segm.tag_keywords:
                            name = k.get_full_name()
                            r[name] = 1
                    f.append(r)
                    c += 1

        if self.export_scr:
            for scr in project.screenshots:  #type:Screenshot
                bodies = scr.get_annotations()
                if len(bodies) == 0:
                    bodies = [AnnotationBody()]

                for bd in bodies:
                    r = dict(
                        ROW = c,
                        ID = scr.unique_id,
                        START_MS = scr.get_start(),
                        END_MS = scr.get_end(),
                        SELECTOR_TYPE = "SCREENSHOT",
                        ANNOTATION_MIME_TYPE=bd.mime_type,
                        ANNOTATION_BODY_ID=bd.unique_id,
                        ANNOTATION_BODY=bd.content,
                        NOTES = scr.notes
                    )
                    if self.export_keywords:
                        for k in keyword_columns:
                            r[k] = 0
                        for k in scr.tag_keywords:
                            name = k.get_full_name()
                            r[name] = 1
                    f.append(r)
                    c += 1
        f.save(path)


class ColorimetryExporter(ExportDevice):
    def __init__(self):
        pass

    def export(self, project:VIANProject, path):
        if project.colormetry_analysis is None:
            raise Exception("Colorimetry has not been performed yet")

        data = np.zeros(shape=(len(project.colormetry_analysis), 6))

        timestamps = []
        for i, entry in enumerate(project.colormetry_analysis.iter_avg_color()):
            l,c,h = lch_to_human_readable([entry['l'], entry['c'],entry['h']])
            data[i] = [
              entry['time_ms'],
              entry['l'],
              entry['a'],
              entry['b'],
              c,
              h,
            ]
            timestamps.append(ms_to_string(entry['time_ms']))

        df = pd.DataFrame(dict(time_ms=data[:, 0],
                               timestamp=timestamps,
                               luminance=data[:, 1],
                               a=data[:, 2],
                               b=data[:, 3],
                               chroma=data[:, 4],
                               hue=data[:, 5]
                               ))

        df.to_csv(os.path.join(project.export_dir, path), index_label="ID")


def build_file_name(naming, screenshot, movie_descriptor):
    """
    Generates a Filename for the Screenshots by a given naming convention
    
    :param naming: 
    :param screenshot: 
    :param movie_descriptor: 
    :return: 
    """
    file_name = "/"

    for i, name in enumerate(naming):
        if name is not ScreenshotNamingConventionOptions.empty.name:
            value = get_enum_value(ScreenshotNamingConventionOptions, name)
            object_type = value[0]
            object_attr = value[1]

            if object_type == "Screenshot":

                # This removed the underline for the ERC Screenshot Groups, but is unpredictable for other users.
                # if object_attr == "screenshot_group":
                #     file_name = file_name[:-1]

                attr = getattr(screenshot, object_attr)
                if isinstance(attr, ScreenshotGroup):
                    attr = attr.get_name()
                file_name += str(attr)

            if object_type == "Movie":
                file_name += str(getattr(movie_descriptor, object_attr))

            if i < len(naming) - 1:
                if get_enum_value(ScreenshotNamingConventionOptions, naming[i + 1])[1] == 0:
                    break
                else:
                    file_name += "_"

    file_name = file_name.replace("__", "")
    file_name = file_name.replace("All Shots_", "_")

    return file_name

def build_segment_nomenclature(s:Segment):
    return str(s.project.movie_descriptor.movie_id) + "_"+ s.segmentation.name +"_" + str(s.ID)