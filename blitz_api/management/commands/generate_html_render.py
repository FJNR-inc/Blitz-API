from django.core.management.base import BaseCommand
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = 'Generate a html file based on a template. Pass path to template' \
           ' as parameter'

    def add_arguments(self, parser):
        parser.add_argument('path_to_template', type=str)

    def handle(self, *args, **options):
        self.stdout.write(f"Generating from template located at "
                          f"{options['path_to_template']}")

        # Use dict below to fill your template data
        merge_data = {}

        msg_html = render_to_string("invoice.html", merge_data)

        destination_render_path = "media/render/"
        filename = f"render_{options['path_to_template'].split('/')[-1]}"
        file_path = f"{destination_render_path}{filename}"
        with open(file_path, "w+") as file:
            file.write(msg_html)

        self.stdout.write(f"Document generated at {file_path}")
