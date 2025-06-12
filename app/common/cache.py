# app/core/cache.py

class AppCache:
    def __init__(self):
        self.git_email = {}
        self.git_id = {}
        self.user_email = {}
        self.user_name = {}
        self.user_infos = []
        self.teams = []

    def load(self, db):
        from app.rdb.repository import find_all_git_info, find_all_teams, find_all_users
        git_infos = find_all_git_info(db)
        self.user_infos = find_all_users(db)

        self.git_email = {
            info.git_email: info.user_id
            for info in git_infos
            if info.git_email
        }

        self.git_id = {
            info.git_id: info.user_id
            for info in git_infos
            if info.git_id
        }

        self.user_email = {
            info.email: info.id
            for info in self.user_infos
            if info.email
        }

        self.user_name = {
            info.name: info.id
            for info in self.user_infos
            if info.name
        }

        self.teams = find_all_teams(db)

app_cache = AppCache()
