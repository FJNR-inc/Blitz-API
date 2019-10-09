FROM lambci/lambda:build-python3.6

LABEL maintainer="support@fjnr.ca"

# Fancy prompt to remind you are in zappashell
RUN echo 'export PS1="\[\e[36m\]blitz_shell>\[\e[m\] "' >> /root/.bashrc

COPY requirements.txt /requirements.txt
COPY requirements-dev.txt /requirements-dev.txt

RUN yum update -y && yum install -y postgresql-devel python3-devel
# Virtualenv created for zappa
RUN virtualenv ~/ve
RUN source ~/ve/bin/activate \
    && pip install -r /requirements.txt \
    && pip install -r /requirements-dev.txt

RUN pip install -r /requirements.txt \
    && pip install -r /requirements-dev.txt

RUN mkdir -p /opt/project

WORKDIR /opt/project

CMD ["bash"]