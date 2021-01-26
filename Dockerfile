FROM python:3.7.0-slim

RUN apt-get update

RUN apt-get -y install libgeos-dev

# Copy the source code
COPY . /PyDSS

# Change directory to the src folder
WORKDIR /PyDSS

RUN pip install --upgrade pip
#RUN pip install --upgrade setuptools

#RUN pip install --index-url https://pypi.naerm.team/simple/ naerm_core

RUN pip install --index-url https://pypi.naerm.team/simple/ \
                -r requirements.txt

# Install the python modules
RUN pip install -e .

ENV PYTHONPATH=/PyDSS/PyDSS/api/src

WORKDIR /PyDSS/PyDSS/api/src

EXPOSE 5000/tcp

# Change directory to the src folder
CMD [ "python", "main.py", "-l", "../logging.yaml", "-e", "../endpoints.yaml", "-c", "config.yaml" ]
