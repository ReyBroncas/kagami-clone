"""ColdEngine class module."""


import os

from .base_engine import BaseEngine


class ColdEngine(BaseEngine):
    def __init__(self, vault_path):
        super(ColdEngine, self).__init__(vault_path)

    def cold_sync(self):
        modified = []
        newly_created = []
        p_hash_set = set(self.hashes.get_phash_list())

        if not os.path.exists(self.hashes.cache_dir):
            os.makedirs(self.hashes.cache_dir)

        for root, d_names, f_names in os.walk(self.vault_path):
            if root in [self.hashes.hash_dir, self.hashes.cache_dir]:
                continue

            for file in f_names:
                file_path = os.path.join(root, file)

                p_hash = self.hashes.gen_path_hash(file_path)

                if p_hash in p_hash_set:
                    p_hash_set.remove(p_hash)
                else:
                    newly_created.append(file_path)
                    continue

                c_hash = self.hashes.get_content_hash(p_hash)
                remote_hash = self.hashes.gen_remote_hash(file_path)

                if remote_hash != c_hash:
                    self.modified_event_handler(file_path, True)
                    modified.append(file_path)

        for p_hash in p_hash_set:
            filepath = self.hashes.get_filepath_from_p_hash(p_hash)
            self.moved_event_handler(filepath, True, p_hash)

        new_files = []
        for filepath in newly_created:
            if self.created_event_handler(filepath, True):
                new_files.append(filepath)

    def moved_event_handler(self, entry_path, is_file=False, p_hash=None):
        """
        Creating t_hash file @ .kagami/cache
        """
        # TODO: add dir handling
        # TODO: add timeout for deletion inside t_hash file
        if p_hash is None:
            p_hash = self.hashes.gen_path_hash(entry_path)

        c_hash = self.hashes.get_content_hash(p_hash)
        t_hash_path = os.path.join(self.hashes.cache_dir, c_hash)

        with open(t_hash_path, "wt") as file:
            file.write(entry_path)

        # Removing previous c_hash file @ .kagami/
        os.remove(os.path.join(self.hashes.hash_dir, p_hash))
        print(f"Added t_hash @ {t_hash_path};\nRemoved hash_file @ {p_hash}")

    def created_event_handler(self, entry_path, is_file=False):
        # TODO: add dir handling
        # TODO: fix bug when moving dublicates with different names
        # possible fix: concativate values inside t_hash file
        c_hash = self.service.hash_file(entry_path)
        t_hash_path = os.path.join(self.hashes.cache_dir, c_hash)

        if os.path.isfile(t_hash_path):
            with open(t_hash_path) as file:
                prev_file = file.read()

            print(f"{prev_file} --> {entry_path}")
            commonprefix = os.path.commonprefix([prev_file, self.vault_path])
            self.service.move_file(prev_file[len(commonprefix):], entry_path[len(commonprefix):])

            # update c_hash
            self.hashes.hash_entry(entry_path, single_file=True)
            # delete t_hash
            os.remove(t_hash_path)
            return False
        else:
            print(f"New file: {entry_path}")
            commonprefix = os.path.commonprefix([entry_path, self.vault_path])
            remote_path = entry_path[len(commonprefix):]
            self.hashes.hash_entry(entry_path, True)
            self.service.upload_file(remote_path, entry_path)
            return True

    def modified_event_handler(self, entry_path, is_file=False):
        # TODO: add dir handling
        commonprefix = os.path.commonprefix([entry_path, self.vault_path])
        remote_path = entry_path[len(commonprefix):]
        self.service.update_file(remote_path, entry_path)
        print("FILE MODIFIED: ", entry_path)
        self.hashes.hash_entry(entry_path, single_file=True)

    @staticmethod
    def _is_file(path) -> bool:
        return os.path.isfile(path)