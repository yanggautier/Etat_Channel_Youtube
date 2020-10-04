# Use the Pythofn 3.8.3 container image
FROM python:3.8.3

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contetns into the container at /app
ADD . /app

COPY . .
# Install the dependencies
RUN pip install -r requirements.txt


ENTRYPOINT ['streamlit', 'run']
# Run the command to start uWSGI
CMD ['app.py']