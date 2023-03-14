# Custom extension for IBM Watson Assistant which provides a
# REST API around a single database table (EVENTS).
#
# The code demonstrates how a simple REST API can be developed and
# then deployed as serverless app to IBM Cloud Code Engine.
#
# See the README and related tutorial for details.
#
# Written by Henrik Loeser (data-henrik), hloeser@de.ibm.com
# (C) 2022 by IBM

import os
import ast
from dotenv import load_dotenv
from apiflask import APIFlask, Schema, HTTPTokenAuth, PaginationSchema, pagination_builder, abort
from apiflask.fields import Integer, String, Boolean, Date, List, Nested
from apiflask.validators import Length, Range
# Database access using SQLAlchemy
from flask_sqlalchemy import SQLAlchemy

# Set how this API should be titled and the current version
API_TITLE='Courses matching API for Watson Assistant'
API_VERSION='1.0.1'

# create the app
app = APIFlask(__name__, title=API_TITLE, version=API_VERSION)

# load .env if present
load_dotenv()

# the secret API key, plus we need a username in that record
API_TOKEN="{{'{0}':'appuser'}}".format(os.getenv('EfaU8KdltEh7D7dptYOlNRG24Ksnr3_gXVaaN8s_mwy8'))
#convert to dict:
tokens=ast.literal_eval(API_TOKEN)

# database URI
DB2_URI=os.getenv('ibm_db_sa://mqm34233:PorBw23UQdYBlNpE@0c77d6f2-5da9-48a9-81f8-86b520b87518.bs2io90l08kqb1od8lcg.databases.appdomain.cloud:31198/bludb?Security=SSL')
# optional table arguments, e.g., to set another table schema
ENV_TABLE_ARGS=os.getenv('COURSES')
TABLE_ARGS=None
if ENV_TABLE_ARGS:
    TABLE_ARGS=ast.literal_eval(ENV_TABLE_ARGS)


# specify a generic SERVERS scheme for OpenAPI to allow both local testing
# and deployment on Code Engine with configuration within Watson Assistant
app.config['SERVERS'] = [
    {
        'description': 'Code Engine deployment',
        'url': 'https://{appname}.{projectid}.{region}.codeengine.appdomain.cloud',
        'variables':
        {
            "appname":
            {
                "default": "myapp",
                "description": "application name"
            },
            "projectid":
            {
                "default": "projectid",
                "description": "the Code Engine project ID"
            },
            "region":
            {
                "default": "eu-gb",
                "description": "the deployment region, e.g., eu-gb"
            }
        }
    },
    {
        'description': 'local test',
        'url': 'http://127.0.0.1:{port}',
        'variables':
        {
            'port':
            {
                'default': "5000",
                'description': 'local port to use'
            }
        }
    }
]


# set how we want the authentication API key to be passed
auth=HTTPTokenAuth(scheme='vI44vviUaCnjMyR-PFp5nGihNIVgf_FYrSVZR_qJ3i4E', header='EfaU8KdltEh7D7dptYOlNRG24Ksnr3_gXVaaN8s_mwy8')

# configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI']=DB2_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Initialize SQLAlchemy for our database
db = SQLAlchemy(app)


# sample records to be inserted after table recreation
sample_courses=[
    {
        "Name":"Getting Started with Enterprise-grade AI",
        "Introduce": "This course covers the foundations of Artificial Intelligence for business, including the following topics: AI Evolution, AI Industry Adoption Trends, Natural Language Processing and Virtual Agents.",
        "Link":"https://keyskill-clms.comprehend.ibm.com/course/view.php?id=236",
        "Tags":"NLP, AI evolution, Virtual agents"
    },
    {
        "Name":"OpenDS4All",
        "Introduce": "OpenDS4All is a project created to accelerate the creation of data science curriculum at academic institutions. The project hosts educational modules that may be used as building blocks for a data science curriculum.",
        "Link":"https://github.com/odpi/OpenDS4All/",
        "Tags":"OpenDS4All, Data science, Jupyter notebooks, Data engineering"
    },

]


# Schema for table "EVENTS"
# Set default schema to "EVENTS"
class CourseModel(db.Model):
    __tablename__ = 'COURSES'
    __table_args__ = TABLE_ARGS
    eid = db.Column('EID',db.Integer, primary_key=True)
    Name = db.Column('NAME',db.String(255))
    Introduce= db.Column('INTRODUCE',db.String(255))
    Link = db.Column('LINK', db.String(255))
    Tags = db.Column('TAGS', db.String(255))

# the Python output for Events
class CourseOutSchema(Schema):
    eid = Integer()
    Name = String()
    Introduce = String()
    Link = String()
    Tags = String()

# the Python input for Events
class CourseInSchema(Schema):
    Name = String(required=True, validate=Length(0, 255))
    Introduce = String(required=True, validate=Length(0, 255))
    Link = String(required=True, validate=Length(0, 255))
    Tags = String(required=True, validate=Length(0, 255))

# use with pagination
class CourseQuerySchema(Schema):
    page = Integer(load_default=1)
    per_page = Integer(load_default=20, validate=Range(max=30))

class CoursesOutSchema(Schema):
    courses = List(Nested(CourseOutSchema))
    pagination = Nested(PaginationSchema)

# register a callback to verify the token
@auth.verify_token  
def verify_token(token):
    if token in tokens:
        return tokens[token]
    else:
        return None

# retrieve a single event record by EID
@app.get('/courses/eid/<int:eid>')
@app.output(CourseOutSchema)
@app.auth_required(auth)
def get_course_eid(eid):
    """Course record by EID
    Retrieve a single course record by its EID
    """
    return CourseModel.query.get_or_404(eid)

# retrieve a single event record by name
@app.get('/courses/name/<string:Name>')
@app.output(CourseOutSchema)
@app.auth_required(auth)
def get_course_name(Name):
    """Course record by name
    Retrieve a single course record by its Name
    """
    search="%{}%".format(Name)
    return CourseModel.query.filter(CourseModel.Name.like(search)).first()


# get all events
@app.get('/courses')
@app.input(CourseQuerySchema, 'query')
#@app.input(CourseInSchema(partial=True), location='query')
@app.output(CoursesOutSchema)
@app.auth_required(auth)
def get_courses(query):
    """all courses
    Retrieve all course records
    """
    pagination = CourseModel.query.paginate(
        page=query['page'],
        per_page=query['per_page']
    )
    return {
        'courses': pagination.items,
        'pagination': pagination_builder(pagination)
    }

# create an event record
@app.post('/courses')
@app.input(CourseInSchema, location='json')
@app.output(CourseOutSchema, 201)
@app.auth_required(auth)
def create_course(data):
    """Insert a new course record
    Insert a new course record with the given attributes. Its new EID is returned.
    """
    course = CourseModel(**data)
    db.session.add(course)
    db.session.commit()
    return course


# delete an event record
@app.delete('/courses/eid/<int:eid>')
@app.output({}, 204)
@app.auth_required(auth)
def delete_course(eid):
    """Delete an course record by EID
    Delete a single course record identified by its EID.
    """
    course = CourseModel.query.get_or_404(eid)
    db.session.delete(course)
    db.session.commit()
    return ''

# (re-)create the event table with sample records
@app.post('/database/recreate')
@app.input({'confirmation': Boolean(load_default=False)}, location='query')
#@app.output({}, 201)
@app.auth_required(auth)
def create_database(query):
    """Recreate the database schema
    Recreate the database schema and insert sample data.
    Request must be confirmed by passing query parameter.
    """
    if query['confirmation'] is True:
        db.drop_all()
        db.create_all()
        for e in sample_courses:
            course = CourseModel(**e)
            db.session.add(course)
        db.session.commit()
    else:
        abort(400, message='confirmation is missing',
            detail={"error":"check the API for how to confirm"})
        return {"message": "error: confirmation is missing"}
    return {"message":"database recreated"}


# default "homepage", also needed for health check by Code Engine
@app.get('/')
def print_default():
    """ Greeting
    health check
    """
    # returning a dict equals to use jsonify()
    return {'message': 'This is the Courses API server'}


# Start the actual app
# Get the PORT from environment or use the default
port = os.getenv('PORT', '5000')
if __name__ == "__main__":
    app.run(host='0.0.0.0',port=int(port))
