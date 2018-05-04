import dataset as ds
import json
from core.corpus.shared.entities import *
from core.data.computation import is_subdir
import glob
import shutil

TABLE_PROJECTS = "PROJECTS"
TABLE_SEGMENTS = "SEGMENTS"
TABLE_SCREENSHOT_GRP = "SCREENSHOT_GROUPS"
TABLE_SCREENSHOTS = "SHOTS"
TABLE_ANNOTATION_LAYERS = "ANNOTATION_LAYERS"
TABLE_SEGMENTATIONS = "SEGMENTATIONS"
TABLE_ANNOTATIONS = "ANNOTATIONS"
TABLE_KEYWORDS = "KEYWORDS"
TABLE_VOCABULARIES = "VOCABULARIES"
TABLE_CLASSIFICATION_OBJECTS = "CLASSIFICATION_OBJECTS"
TABLE_CONTRIBUTORS = "CONTRIBUTORS"

ALL_TABLES = [
    TABLE_PROJECTS,
    TABLE_SEGMENTS,
    TABLE_SCREENSHOTS,
    TABLE_ANNOTATIONS,
    TABLE_KEYWORDS
]

class CorpusDB():
    def __init__(self):
        self.name = ""
        self.root_dir = ""
        self.file_path = ""

    def commit_project(self, project:VIANProject):
        """
        If the project does not yet exist in the Database it is created, 
        else, it is updated, and checked in.
        :param project: 
        :return: 
        """
        pass

    def checkout_project(self, project_id, contributor=DBContributor):
        pass

    def get_project_path(self, dbproject: DBProject):
        pass

    def import_dataset(self, csv_dataset):
        pass

    def initialize(self, name, root_dir):
        self.name = name
        self.root_dir = root_dir + "/" + name + "/"

        if not os.path.isdir(self.root_dir):
            os.mkdir(self.root_dir)

        self.create_file_system(self.root_dir)
        self.file_path = self.root_dir + "/" + self.name + ".vian_corpus"
        self.save(self.file_path)

    def create_file_system(self, root):
        os.mkdir(root + SCR_DIR)
        os.mkdir(root + MOVIE_DIR)
        os.mkdir(root + ANALYSIS_DIR)
        os.mkdir(root + PROJECTS_DIR)

    def connect(self, path):
        pass

    def disconnect(self):
        pass

    def remove_project(self, dbproject: DBProject):
        pass

    def add_user(self, contributor: DBContributor):
        table = self.db[TABLE_CONTRIBUTORS]
        table.inser(contributor.to_database())

    #region Querying
    def get_projects(self, filters):
        pass

    def get_annotation_layers(self, filters):
        pass

    def get_segmentations(self, filters):
        pass

    def get_segments(self, filters):
        pass

    def get_screenshots(self, filters):
        pass

    def get_annotations(self, filters):
        pass

    def get_vocabularies(self):
        pass

    def get_analysis_results(self, filters):
        pass

    def get_words(self):
        pass

    def get_settings(self):
        pass

    # endregion Querying

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.__dict__, f)

    def load(self, path):
        with open(path, "r") as f:
            data = json.load(f)
            for attr, value in data.items():
                setattr(self, attr, value)

    def clear(self, tables = None):
        pass


class DatasetCorpusDB(CorpusDB):
    def __init__(self):
        super(DatasetCorpusDB, self).__init__()
        self.sql_path = ""
        self.db = None
        pass

    def connect(self, path):
        self.path = path
        self.db = ds.connect(path)

    def disconnect(self):
        pass

    def initialize(self, name, root_dir):
        CorpusDB.initialize(self, name, root_dir)
        self.sql_path = 'sqlite:///' + self.root_dir + "/" +self.name + ".vian_corpus_sql"
        print(self.sql_path)
        print(self.root_dir)
        print(self.file_path)
        self.db = ds.connect(self.sql_path)
        self.db.begin()
        self.db["SETTINGS"].insert(dict(name=name, root_dir=root_dir, created=str(get_current_time())))
        self.db.commit()
        self.save(self.file_path)

    def commit_project(self, project: VIANProject, contributor: DBContributor):
        """
        
        :param project: 
        :return: 
        """
        project_obj = DBProject().from_project(project)

        table = self.db[TABLE_PROJECTS]


        #region Check if Project exists
        existing = False
        existing_proj = None
        local_project = self.get_project(project_obj.project_id)
        if local_project is not None:
            existing = True
        #endregion

        # Is Project Checked Out by another User?
        if existing and local_project.is_checked_out:
            return False, "Project is checked out by another User"

        try:
            self.db.begin()
            # Zip the Project and store it in the projects directory
            archive_file = self.root_dir + PROJECTS_DIR + project.name
            project_obj = DBProject().from_project(project)
            shutil.make_archive(archive_file, 'zip', project.folder)
            project_obj.archive = archive_file + ".zip"

            # Make an entry in the Corpus Project Table
            if existing:
                d = project_obj.to_database(include_id=True)
                table.update(d, ['id'])
                # Check if the Heavy files need to be updated:

            else:
                d = project_obj.to_database(include_id=False)
                table.insert(d)
                res = table.find_one(**project_obj.to_database(include_id=False))
                project.corpus_id = res['id']

            self.db.commit()

            self.checkin_project(project.corpus_id, contributor)
            return True, project_obj
        except Exception as e:
            print(e)
            self.db.rollback()
            return False, str(e)

    def checkout_project(self, project_id, contributor:DBContributor):
        project = self.get_project(project_id)

        # If the project is not checked out at all
        if not project.is_checked_out:
            project.is_checked_out = True
            project.checked_out_user = contributor.contributor_id
            self.db.begin()
            self.db[TABLE_PROJECTS].update(project.to_database(True), ['id'])
            self.db.commit()

            return True, project.archive
        else:
            # If the project is checked out by this user
            if project.checked_out_user == contributor.contributor_id:
                return True, project.archive
            # Else it is checked out by another user
            else:
                return False, None

    def checkin_project(self, project_id, contributor:DBContributor):
        user = self.get_users(dict(id=contributor.contributor_id))
        local_project = self.get_project(project_id)
        if len(user) > 0 and local_project is not None:
            if int(local_project.checked_out_user) == int(user[0].contributor_id):
                try:
                    self.db.begin()
                    local_project.is_checked_out = False
                    local_project.checked_out_user = -1
                    self.db[TABLE_PROJECTS].update(local_project.to_database(True), ['id'])
                    self.db.commit()
                    return True
                except Exception as e:
                    print(e)
                    self.db.rollback()
            else:
                print("User not regconized or not matching the Check Out User")
        return False

    def remove_project(self, dbproject: DBProject):
        local_project = self.get_project(dbproject.project_id)
        try:
            os.remove(local_project.archive)
        except Exception as e:
            print("Exception in CorpusDB:remove_project(): ", e)
        self.db[TABLE_PROJECTS].delete(id=dbproject.project_id)

    def import_dataset(self, csv_dataset):
        pass

    def clear(self, tables = None):
        self.db[TABLE_PROJECTS].drop()

    #region Users
    def add_user(self, contributor: DBContributor):
        try:
            self.db.begin()
            table = self.db[TABLE_CONTRIBUTORS]
            contributor.contributor_id = table.insert(contributor.to_database())
            self.db.commit()
        except Exception as e:
            print("Exception in CorpusDB:add_user(): ", str(e))
            self.db.rollback()

    def connect_user(self, contributor: DBContributor):
        users = self.get_users(dict(id=contributor.contributor_id))
        if len(users) == 0:
            self.add_user(contributor)
            return contributor
        else:
            return users[0]

    def remove_user(self, contributor:DBContributor):
        try:
            self.db.begin()
            self.db[TABLE_CONTRIBUTORS].delete(id=contributor.contributor_id)
            self.db.commit()
        except Exception as e:
            print("Exception in CorpusDB:remove_user(): ", str(e))
            self.db.rollback()

    def get_users(self, filters = None):
        if filters is None:
            query = self.db[TABLE_CONTRIBUTORS].find_all()
        else:
            query = self.db[TABLE_CONTRIBUTORS].find(**filters)

        result = []
        for q in query:
            result.append(DBContributor("", "").from_database(q))
        return result

    #endregion

    #region Query
    def get_project(self, project_id):
        project = self.db[TABLE_PROJECTS].find_one(id=project_id)
        if project is None:
            return None

        dbproject = DBProject().from_database(project)
        return dbproject

    def get_projects(self, filters = None):
        if filters is None:
            query = self.db[TABLE_PROJECTS].all()
        else:
            query = self.db[TABLE_PROJECTS].find(**filters)
        result = []
        for r in query:
            result.append(DBProject().from_database(r))
        return result

    def get_project_path(self, dbproject: DBProject):
        for r in self.get_projects(filters=dict(id=dbproject.project_id)):
            return r.archive
        return None

    def get_annotation_layers(self, filters = None):
        if filters is None:
            return self.db[TABLE_ANNOTATION_LAYERS].all()
        return self.db[TABLE_ANNOTATION_LAYERS].find(**filters)

    def get_segmentations(self, filters = None):
        if filters is None:
            return self.db[TABLE_SEGMENTATIONS].all()
        return self.db[TABLE_SEGMENTATIONS].find(**filters)

    def get_segments(self, filters = None):
        if filters is None:
            return self.db[TABLE_SEGMENTS].all()
        return self.db[TABLE_SEGMENTS].find(**filters)

    def get_screenshots(self, filters = None):
        if filters is None:
            return self.db[TABLE_SCREENSHOTS].all()
        return self.db[TABLE_SCREENSHOTS].find(**filters)

    def get_annotations(self, filters = None):
        if filters is None:
            return self.db[TABLE_ANNOTATIONS].all()
        return self.db[TABLE_ANNOTATIONS].find(**filters)

    def get_vocabularies(self, filters = None):
        if filters is None:
            return self.db[TABLE_VOCABULARIES].all()
        return self.db[TABLE_VOCABULARIES].find(**filters)

    def get_classification_objects(self, filters = None):
        if filters is None:
            return self.db[TABLE_CLASSIFICATION_OBJECTS].all()
        return self.db[TABLE_CLASSIFICATION_OBJECTS].find(**filters)

    def get_settings(self):
        pass

    def get_words(self, filters = None):
        if filters is None:
            return self.db[TABLE_KEYWORDS].all()
        return self.db[TABLE_KEYWORDS].find(**filters)

    #endregion

    #region IO
    def save(self, path):
        with open(path, "w") as f:
            data = dict(
                name = self.name,
                file_path = self.file_path,
                root_dir = self.root_dir,
                sql_path = self.sql_path
            )
            json.dump(data, f)

    def load(self, path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
                for attr, value in data.items():
                    setattr(self, attr, value)
            self.connect(self.sql_path)
        except Exception as e:
            print(e)
            return False
        return self
    #endregion


