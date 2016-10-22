import os, shutil, dotbot, pwd, grp

class Copy(dotbot.Plugin):
    '''
    Copy dotfiles
    '''

    _directive = 'copy'

    def _chmodown(self, path, chmod, uid, gid):
        os.chmod(path, chmod)
        os.chown(path, uid, gid)

    def _expand(self, path):
        return os.path.expandvars(os.path.expanduser(path))

    def can_handle(self, directive):
        return directive == self._directive

    def handle(self, directive, data):
        if directive != self._directive:
            raise ValueError('Copy cannot handle directive %s' % directive)
        return self._process_records(data)

    def _process_records(self, records):
        success = True
        defaults = self._context.defaults().get('copy', {})
        for destination, source in records.items():
            destination = self._expand(destination)
            force = defaults.get('force', False)
            create = defaults.get('create', False)
            # python3 only
            fmode = defaults.get('fmode', 0o644)
            dmode = defaults.get('dmode', 0o755)
            owner = defaults.get('owner', pwd.getpwuid(os.getuid()).pw_name)
            group = defaults.get('group', grp.getgrgid(os.getgid()).gr_name)
            if isinstance(source, dict):
                # extended config
                force = source.get('force', force)
                create = source.get('create', create)
                fmode = source.get('fmode', fmode)
                dmode = source.get('dmode', dmode)
                owner = source.get('owner', owner)
                group = source.get('group', group)
                path = source['path']
            else:
                path = source
            uid = pwd.getpwnam(owner).pw_uid
            gid = grp.getgrnam(group).gr_gid
            if force:
                success &= self._delete(destination)
            if create:
                success &= self._create(destination, dmode, uid, gid)
            path = self._expand(path)
            success &= self._copy(path, destination, dmode, fmode, uid, gid)
        if success:
            self._log.info('All copies have been set up')
        else:
            self._log.error('Some copies were not successfully set up')
        return success

    def _delete(self, path):
        success = False
        try:
            if os.path.islink(path):
                os.unlink(path)
                self._log.lowinfo('Removing link %s' % path)
            elif os.path.isfile(path):
                os.remove(path)
                self._log.lowinfo('Removing file %s' % path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
                self._log.lowinfo('Removing directory %s' % path)
        except (OSError, shutil.Error) as e :
            self._log.warning('Failed to remove %s. %s' % (path, e))
        else:
            success = True
        return success

    def _create(self, path, dmode, uid, gid):
        success = True
        parent = os.path.abspath(os.path.join(path, os.pardir))
        if not os.path.exists(parent):
            try:
                os.mkdir(parent, dmode)
                self._chmodown(parent, dmode, uid, gid)
            except OSError as e:
                self._log.warning('Failed to create directory %s. %s' % (parent, e))
                success = False
            else:
                self._log.lowinfo('Creating directory %s' % parent)
        return success

    def _copy(self, source, destination, dmode, fmode, uid, gid):
        '''
        Copies source to destination

        Returns true if successfully copied files.
        '''
        success = False
        source = os.path.join(self._context.base_directory(), source)
        destination = os.path.expanduser(destination)
        try:
            if os.path.isdir(source):
                # python3 only
                shutil.copytree(source, destination, symlinks=True, copy_function=shutil.copy)
                for root, dirs, files in os.walk(destination):
                    self._chmodown(root, dmode, uid, gid)
                    for d in dirs:
                        self._chmodown(os.path.join(root, d), dmode, uid, gid)
                    for f in files:
                        self._chmodown(os.path.join(root, f), fmode, uid, gid)
            else:
                # python3 only
                shutil.copyfile(source, destination, follow_symlinks=False)
                self._chmodown(destination, fmode, uid, gid)
        except (OSError, shutil.Error) as e:
            self._log.warning('Failed to copy %s -> %s. %s' % (source, destination, e))
        else:
            self._log.lowinfo('Copied %s -> %s' % (source, destination))
            success = True
        return success
