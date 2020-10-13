# This app is used to analyse youtube channel and use sentiment analysis at comments of video

Use virtualenv to install packages required to this app
1. Pip
`
pip install virtualenv
`

2. Create virtual environment
`
virtualenv venv
`

3. Activate virtual environment
Linux:
```shell
$ cd venv
$ source ./bin/activate
```

Windows 10:
```shell
cd venv
.\Scripts\activate.bat
```

4. Install packages
```shell
pip install -r requirements.txt
```

# Structure
`
app
  -static
    -css
    -img
    -js
    -scss
    -vendor
  -templates
    -index.html
  -app.py
  -cred.py
scrap
  -channel.py
  -video.py
comments
  -comment.py
models
  -channel_analyse.py
  -video_analyse.py
Dockerfile
requirements.txt
docker-compose.yml
README.md
`