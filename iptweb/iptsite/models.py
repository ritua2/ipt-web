import json
import os


class IPTError(Exception):
    def __init__(self, msg):
        self.message = msg


class IPTModelError(IPTError):
    pass


def get_ipt_instance():
    """Return the IPT instance string, default to using the dev instance."""
    return os.environ.get('IPT_INSTANCE', 'dev')

def get_metatdata_name(username):
    """ Return the name associated with a metadata record for a given username and IPT instance.
    :param user:
    :param instance:
    :return:
    """
    instance = get_ipt_instance()
    return '{}.{}.IPT'.format(username, instance)

def get_user(meta_name):
    """Return the username associated with a meta records name field."""
    return meta_name.split('.')[0]

def is_ipt_meta(m):
    """Check whether a metadata record, m, is associated with this IPT instance."""
    value = m.get('value')
    # IPT metadata records are dictionaries that have a name field:
    if not hasattr(value, 'get'):
        return False
    name = value.get('name')
    if not name:
        return False
    # the name field should have three parts separated by periods:
    name_parts = name.split('.')
    if not (len(name_parts) == 3):
        return False
    if not (name_parts[1] == get_ipt_instance()):
        return False
    if not (name_parts[2] == 'IPT'):
        return False
    return True

class TerminalMetadata(object):
    """Model to hold metadata about a specific user's terminal session."""

    pending_status = "PENDING"
    submitted_status = "SUBMITTED"
    ready_status = "READY"
    stopped_status = "STOPPED"
    error_status = "ERROR"

    def _get_meta_dict(self, status, url=""):
        """Returns the basic Python dictionary containing the metadata to be stored in Agave."""
        return {"name": self.name,
                "value": {"name": self.name,
                          "status": status,
                          "url": url}}

    def _get_meta(self, ag):
        """Retrieve the meta record from Agave using the agave client, `ag`."""
        try:
            records = ag.meta.listMetadata(search={'name.eq': get_metatdata_name(self.user)})
        except Exception as e:
            # todo - figure out logging
            msg = "Python exception trying to get the meta record for user {}. Exception: {}".format(self.user, e)
            raise IPTModelError(msg)
        for m in records:
            if m['name'] == self.name:
                self.uuid = m['uuid']
                self.value = m['value']
                return m
        else:
            raise IPTModelError("Did not find meta record for user: {}".format(self.name))

    def _create_meta(self, ag):
        """Create the meta record in Agave using the agave client, `ag`. """
        name = get_metatdata_name(self.user)
        d = self._get_meta_dict(self.pending_status)
        try:
            m = ag.meta.addMetadata(body=json.dumps(d))
        except Exception as e:
            # todo - figure out logging
            msg = "Exception trying to create the meta record for user {}. Exception: {}".format(self.user, e)
            raise IPTModelError(msg)
        self.uuid = m['uuid']
        self.value = m['value']
        # share the metadata with the service account
        service_account = os.environ.get('AGAVE_SERVICE_ACCOUNT', "apitest")
        try:
            ag.meta.updateMetadataPermissions(uuid=self.uuid,
                                              body={'permission':'READ_WRITE',
                                                    'username': service_account})
        except Exception as e:
            msg = "Exception trying to share the meta record for user: {}. Exception:{}".format(self.user, e)
            raise IPTModelError(msg)

    def _update_meta(self, ag, d):
        """Update the metadata record value to the data in `d`, a dictionary."""
        if not hasattr(self, 'uuid') or not self.uuid:
            raise IPTModelError("TerminalMetadata object has no uuid.")
        if not d:
            raise IPTModelError("dictionary required for updating metadata.")
        try:
            m = ag.meta.updateMetadata(uuid=self.uuid, body=d)
        except Exception as e:
            # todo - figure out logging
            msg = "Python exception trying to update the meta record for user {}. Exception: {}".format(self.user, e)
            raise IPTModelError(msg)
        self.value = m['value']

    def __init__(self, user, ag):
        """
        Construct a metadata object representing a user and an IPT instance. This constructor will attempt to fetch
        the associated metadata record from Agave, but if it does not exist it will create it automatically. In
        the later case, the metadata record will be created in PENDING status.
        """
        if not user:
            raise IPTModelError("no user defined.")
        self.instance = get_ipt_instance()
        self.user = user
        self.name = get_metatdata_name(user)
        self.metadata_name = get_metatdata_name(user)
        self.ag = ag
        try:
            # try to retrieve the metadata record from agave
            self._get_meta(ag)
        except IPTModelError:
            # if that failed, assume the user does not yet have a meta data record and create one now:
            m = self._create_meta(ag)

    def set_submitted(self):
        """Update the status on the user's metadata record for a submitted terminal session."""
        d = self._get_meta_dict(status=self.submitted_status, url="")
        return self._update_meta(self.ag, d)

    def set_ready(self, url):
        """Update the status and URL on the user's metadata record for a ready terminal session."""
        d = self._get_meta_dict(status=self.ready_status, url=url)
        return self._update_meta(self.ag, d)

    def set_error(self, url=None):
        """Update the status to error on the user's metadata record for a failed terminal session."""
        # if they don't pass a URL, simply use what is already in the metadata.
        if not url:
            url = self.value['url']
        d = self._get_meta_dict(status=self.error_status, url=url)
        return self._update_meta(self.ag, d)

    def set_stopped(self):
        """Update the status to stopped on the user's metadata record for a stopped terminal session."""
        d = self._get_meta_dict(status=self.stopped_status, url='')
        return self._update_meta(self.ag, d)

    def set_pending(self):
        """Update the status to pending on the user's metadata record for a stopped terminal session."""
        d = self._get_meta_dict(status=self.stopped_status, url='')
        return self._update_meta(self.ag, d)

    def get_status(self):
        """Return the status of associated with this terminal,."""
        # refresh the object's representation from Agave:
        return self.value['status']