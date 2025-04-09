from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
import time
import pymysql
from dotenv import load_dotenv

# Load local .env variables (useful for development or Docker with env file)
load_dotenv()

app = Flask(__name__)

# Environment variables
DBHOST = os.getenv("DBHOST", "localhost")
DBPORT = int(os.getenv("DBPORT", 3306))
DBUSER = os.getenv("DBUSER", "root")
DBPWD = os.getenv("DBPWD", "password")
DATABASE = os.getenv("DATABASE", "employees")

GROUP_NAME = os.getenv("GROUP_NAME", "Team CloudOps")
GROUP_SLOGAN = os.getenv("GROUP_SLOGAN", "We scale what matters!")

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
IMAGE_KEY = os.getenv("S3_IMAGE_KEY", "background.jpg")

# Generate presigned URL for background image
BACKGROUND_IMAGE_URL = ""
try:
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        aws_session_token=AWS_SESSION_TOKEN,
        region_name=AWS_REGION
    )
    s3 = session.client("s3")
    BACKGROUND_IMAGE_URL = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': IMAGE_KEY},
        ExpiresIn=3600  # 1 hour
    )
    print("✅ Presigned URL generated for S3 image")
except Exception as e:
    print("❌ Failed to generate S3 presigned URL:", e)

# MySQL connection
print("🔌 Connecting to MySQL...")
connected = False
for i in range(20):
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
        print(f"⏳ Waiting for MySQL... ({i+1}/20)")
        time.sleep(3)

if not connected:
    print("❌ Could not connect to MySQL. Exiting.")
    exit(1)

# ROUTES

@app.route("/")
def home():
    return render_template("addemp.html",
                           group_name=GROUP_NAME,
                           group_slogan=GROUP_SLOGAN,
                           background_image=BACKGROUND_IMAGE_URL)

@app.route("/about")
def about():
    return render_template("about.html",
                           group_name=GROUP_NAME,
                           group_slogan=GROUP_SLOGAN,
                           background_image=BACKGROUND_IMAGE_URL)

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

    return render_template("addempoutput.html",
                           name=emp_name,
                           group_name=GROUP_NAME,
                           background_image=BACKGROUND_IMAGE_URL)

@app.route("/getemp")
def GetEmp():
    return render_template("getemp.html",
                           group_name=GROUP_NAME,
                           background_image=BACKGROUND_IMAGE_URL)

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
                                   group_name=GROUP_NAME,
                                   background_image=BACKGROUND_IMAGE_URL)
        else:
            return "No employee found."
    except Exception as e:
        return str(e)
    finally:
        cursor.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=81)
