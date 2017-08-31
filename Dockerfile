FROM vinodsharma/python:2.7-devel
ENV APPDIR=/opt/thestral
RUN /usr/bin/virtualenv venv
RUN source venv/bin/activate
RUN mkdir $APPDIR
COPY . $APPDIR/requirements.txt
WORKDIR $APPDIR
RUN pip install --upgrade --no-cache-dir -r requirements.txt
