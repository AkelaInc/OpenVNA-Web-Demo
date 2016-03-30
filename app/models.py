

from hashlib import md5
import re
from app import db
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import event
from sqlalchemy.schema import DDL
from sqlalchemy import Table

import sqlalchemy.exc
import datetime
from sqlalchemy import CheckConstraint



class HttpRequestLog(db.Model):
	id             = db.Column(db.Integer, primary_key=True)
	access_time    = db.Column(db.DateTime, nullable=False, index=True, default=datetime.datetime.utcnow)
	path           = db.Column(db.String)
	user_agent     = db.Column(db.String)
	referer        = db.Column(db.String)
	forwarded_for  = db.Column(db.String)
	originating_ip = db.Column(db.String)
	operation      = db.Column(db.String)