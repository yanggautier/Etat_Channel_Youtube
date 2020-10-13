#FROM ubuntu:latest
FROM python:3.8

RUN mkdir -p /project
# Set the working directory to /app
WORKDIR /project

COPY . /project
# Copy the current directory contents into the container at /app
# Update apt-get sources AND install Python-dve
RUN pip3 install -r requirements.txt

EXPOSE 5000

CMD ["python" , "/app/app.py"]