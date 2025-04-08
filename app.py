from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
import requests
import time
import pymysql
from dotenv import load_dotenv

# Load from .env for local testing (optional, ignored in Docker/K8s)
load_dotenv()

app = Flask(__name__)

# Load environment config
DBHOST = os.getenv("DBHOST", "localhost")
DBPORT = int(os.getenv("DBPORT", 3306))
DBUSER = os.getenv("DBUSER", "root")
DBPWD = os.getenv("DBPWD", "password")
DATABASE = os.getenv("DATABASE", "employees")

GROUP_NAME = os.getenv("GROUP_NAME", "Team CLO835")
GROUP_SLOGAN = os.getenv("GROUP_SLOGAN", "Scaling the future")

BACKGROUND_URL = os.getenv("BACKGROUND_IMAGE_URL", "https://vectorified.com/images/kubernetes-icon-14.png")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
IMAGE_KEY = os.getenv("S3_IMAGE_KEY", "background.jpg")

# Download background image
background_path = os.path.join("static", "background.jpg")
if not os.path.exists("static"):
    os.makedirs("static")

try:
    print(f"📥 Background image URL: {BACKGROUND_URL}")
    if AWS_ACCESS_KEY and AWS_SECRET_KEY and BUCKET_NAME and IMAGE_KEY:
        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )
        s3 = session.client("s3")
        s3.download_file(BUCKET_NAME, IMAGE_KEY, background_path)
        print("✅ Image downloaded from S3")
    else:
        response = requests.get(BACKGROUND_URL)
        if response.status_code == 200:
            with open(background_path, "wb") as f:
                f.write(response.content)
            print("✅ Image downloaded from URL")
except Exception as e:
    print("❌ Failed to download background image:", e)

# Wait for MySQL to be ready
print("🔌 Connecting to MySQL...")
connected = False
for i in range(10):
    try:
        db_conn = connections.Connection(
            host=DBHOST,
            port=DBPORT,
            user=DBUSER,
            password=DBPWD,
            db=DATABASE
        )
        print("✅ Connected to MySQL")
        connected = True
        break
    except pymysql.err.OperationalError as e:
        print(f"⏳ Waiting for MySQL... ({i+1}/10)")
        time.sleep(3)

if not connected:
    print("❌ Could not connect to MySQL. Exiting.")
    exit(1)

@app.route("/")
def home():
    return render_template("addemp.html", group_name=GROUP_NAME, group_slogan=GROUP_SLOGAN)

@app.route("/about")
def about():
    return render_template(
        "about.html",
        group_name=GROUP_NAME,
        group_slogan=GROUP_SLOGAN,
        background_image="background.jpg"
    )

@app.route("/addemp", methods=["POST"])
def AddEmp():
    emp_id = request.form["emp_id"]
    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    primary_skill = request.form["primary_skill"]
    location = request.form["location"]

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    try:
        cursor.execute(insert_sql, (emp_id, first_name, last_name, primary_skill, location))
        db_conn.commit()
        emp_name = f"{first_name} {last_name}"
    finally:
        cursor.close()

    return render_template("addempoutput.html", name=emp_name, group_name=GROUP_NAME)

@app.route("/getemp")
def GetEmp():
    return render_template("getemp.html", group_name=GROUP_NAME)

@app.route("/fetchdata", methods=["POST"])
def FetchData():
    emp_id = request.form["emp_id"]
    select_sql = "SELECT emp_id, first_name, last_name, primary_skill, location FROM employee WHERE emp_id=%s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (emp_id,))
        result = cursor.fetchone()
        if result:
            return render_template("getempoutput.html",
                                   id=result[0], fname=result[1], lname=result[2],
                                   interest=result[3], location=result[4],
                                   group_name=GROUP_NAME)
        else:
            return "No employee found."
    except Exception as e:
        return str(e)
    finally:
        cursor.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=81)
