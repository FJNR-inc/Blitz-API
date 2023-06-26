FROM lambci/lambda:build-python3.8

LABEL maintainer="support@fjnr.ca"

# Fancy prompt to remind you are in zappashell
RUN echo 'export PS1="\[\e[36m\]blitz_shell>\[\e[m\] "' >> /root/.bashrc

COPY requirements.txt /requirements.txt
COPY requirements-dev.txt /requirements-dev.txt

# Virtualenv created for zappa
RUN virtualenv ~/ve
RUN source ~/ve/bin/activate \
    && pip install -r /requirements.txt \
    && pip install -r /requirements-dev.txt

RUN pip --timeout=1000 install -r /requirements.txt \
    && pip --timeout=1000 install -r /requirements-dev.txt

RUN mkdir -p /opt/project

COPY ./docker/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./docker/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

WORKDIR /opt/project

ENTRYPOINT ["/entrypoint"]