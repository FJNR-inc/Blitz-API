FROM lambci/lambda:build-python3.6

LABEL maintainer="support@fjnr.ca"

WORKDIR /opt/project

# Fancy prompt to remind you are in zappashell
RUN echo 'export PS1="\[\e[36m\]fblitz_shell>\[\e[m\] "' >> /root/.bashrc

# Add management command who required virtualenv
RUN printf '#!/bin/bash \n source ~/ve/bin/activate \n python manage.py createsuperuser' > /usr/bin/createsuperuser
RUN chmod +x /usr/bin/createsuperuser

RUN printf '#!/bin/bash \n source ~/ve/bin/activate \n python manage.py migrate' > /usr/bin/migrate
RUN chmod +x /usr/bin/migrate

RUN printf '#!/bin/bash \n source ~/ve/bin/activate \n python manage.py makemigrations' > /usr/bin/makemigrations
RUN chmod +x /usr/bin/makemigrations

RUN printf '#!/bin/bash \n source ~/ve/bin/activate \n python -u manage.py runserver 0.0.0.0:8000' > /usr/bin/runserver
RUN chmod +x /usr/bin/runserver

RUN printf '#!/bin/bash \n source ~/ve/bin/activate \n zappa update dev' > /usr/bin/zappa_update_dev
RUN chmod +x /usr/bin/zappa_update_dev

RUN printf '#!/bin/bash \n source ~/ve/bin/activate \n zappa deploy dev' > /usr/bin/zappa_deploy_dev
RUN chmod +x /usr/bin/zappa_deploy_dev

RUN printf '#!/bin/bash \n source ~/ve/bin/activate \n python manage.py import_field_templates \n python manage.py import_form_templates \n python manage.py refresh_page_home_template' > /usr/bin/update_data
RUN chmod +x /usr/bin/update_data

COPY requirements.txt /requirements.txt

# Virtualenv created for zappa
RUN virtualenv ~/ve
RUN source ~/ve/bin/activate && pip install -r /requirements.txt
RUN pip install -r /requirements.txt

CMD ["bash"]