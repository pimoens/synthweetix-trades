FROM python:3.7-slim

WORKDIR /usr/src/app
RUN apt-get update -y && apt-get install --no-install-recommends libgomp1

COPY requirements.txt ./
RUN pip install -U pip
RUN pip install -r requirements.txt

COPY . .

CMD [ "python", "./main.py" ]
