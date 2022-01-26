from django.core.management.commands.makemessages import (
    Command as MakeMessagesCommand
)


class Command(MakeMessagesCommand):

    def write_po_file(*args, **kwargs):
        """Overwrite method to do nothing.
        We do not want to interfere with Weblate's
        "Update PO files to match POT (msgmerge)" addon
        """
        pass
