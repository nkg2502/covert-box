'''
	firenze prototype
'''
import os
import urllib
import hashlib
import uuid
from datetime import datetime
from datetime import timedelta 

import logging

from google.appengine.ext import ndb

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

from google.appengine.api import mail

import webapp2
import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(
		loader = jinja2.FileSystemLoader(os.path.dirname(__file__)),
		extensions = ['jinja2.ext.autoescape'],
		autoescape = True)

class CovertBox(ndb.Model):
	blob_key = ndb.BlobKeyProperty()
	file_name = ndb.StringProperty()
	one_time = ndb.BooleanProperty()
	msg = ndb.StringProperty()
	expiry_date = ndb.DateTimeProperty()

class MainHandler(webapp2.RequestHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/upload')

		page = JINJA_ENVIRONMENT.get_template('pages/boxing.html')

		self.response.out.write(page.render({'upload_url': upload_url}))

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
	def post(self):
		upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
		user_key = self.request.get('user_key')
		email = self.request.get('email')
		one_time = self.request.get('one_time')
		msg = self.request.get('msg')
		
		redirect_url = '/error'
		retrieval_key = None

		# email address validation
		message = None
		if '' != email:

			user_key = hashlib.sha512(str(uuid.uuid4().get_hex()) + email).hexdigest()

			salt = hashlib.sha512(user_key + user_key).hexdigest()
			retrieval_key = hashlib.sha512(salt + user_key + salt).hexdigest()

			message = mail.EmailMessage(
					sender="? Covert-Box ?<covert-box@appspot.gserviceaccount.com>",
					subject='"{}" has been uploaded'.format(upload_files[0].filename))

			message.to = "<" + email + ">"
			message.body = """Dear You,
retrieval key: {}

your message: {}
? Covert-Box ?
""".format(user_key, msg)

		elif '' != user_key: # user_key validation

			salt = hashlib.sha512(user_key + user_key).hexdigest()
			retrieval_key = hashlib.sha512(salt + user_key + salt).hexdigest()

		uploaded_files = []
		for f in upload_files:
			box_instance = CovertBox(parent=ndb.Key('retrieval_key', str(retrieval_key)))

			file_name = f.filename
			try:
				encoded_str = email.header.decode_header(box_instance.file_name)

				if not encoded_str[0][1]:
					file_name = encoded_str[0][0].decode(encoded_str[0][1])
			except:
				pass

			box_instance.blob_key = f.key()
			box_instance.file_name = file_name
			box_instance.msg = msg
			box_instance.one_time = True if one_time else False
			box_instance.expiry_date = datetime.now() + timedelta(hours=24)

			box_instance.put()

			uploaded_files.append({
				'name': file_name, 
				'expiry_date': box_instance.expiry_date
			})

		page_value = {
				'uploaded_list': uploaded_files
		}

		page = JINJA_ENVIRONMENT.get_template('pages/boxed.html')
		self.response.out.write(page.render(page_value))

		try:
			message.send()
		except:
			pass

class DownloadHandler(webapp2.RequestHandler):
	def get(self):
		page = JINJA_ENVIRONMENT.get_template('pages/opening.html')
		self.response.out.write(page.render())

	def post(self):
		page = JINJA_ENVIRONMENT.get_template('pages/opened.html')

		user_key = self.request.get('user_key')
		
		salt = hashlib.sha512(user_key + user_key).hexdigest()
		retrieval_key = hashlib.sha512(salt + user_key + salt).hexdigest()

		box_query = CovertBox.query(ancestor=ndb.Key('retrieval_key', str(retrieval_key)), filters=CovertBox.expiry_date > datetime.now())
		box_list = box_query.fetch()

		page_value = {
				'list': box_list,
				'time': datetime.now()
		}

		self.response.out.write(page.render(page_value))

class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
	def get(self, resource):
		resource = str(urllib.unquote(resource))
		blob_info = blobstore.BlobInfo.get(resource)

		is_error = False
		try:
			self.send_blob(blob_info, save_as=blob_info.filename)

			box_instance = CovertBox.query(CovertBox.blob_key == blob_info.key()).get()
			if box_instance.one_time:
				box_instance.expiry_date = datetime.now() - timedelta(hours=25)
				box_instance.put()

		except:
			is_error = True

		if is_error:
			self.redirect('/error')

class DeleteHandler(blobstore_handlers.BlobstoreDownloadHandler):
	def get(self, resource):
		resource = str(urllib.unquote(resource))
		blob_info = blobstore.BlobInfo.get(resource)

		box_instance = None

		if blob_info:
			box_instance = CovertBox.query(CovertBox.blob_key == blob_info.key()).get()
		
		try:
			blob_info.delete()
		except:
			pass

		try:
			box_instance.key.delete()
		except:
			pass

		self.redirect('/opening')

class ErrorHandler(webapp2.RequestHandler):
	def get(self):
		page = JINJA_ENVIRONMENT.get_template('pages/error.html')
		self.response.out.write(page.render({}))

class GarbageFlushHandler(webapp2.RequestHandler):
	def get(self):

		# used +7 hours time
		# because blob server time and data store time is different
		garbage_list = blobstore.BlobInfo.all().filter('creation <', datetime.now() + timedelta(hours=7) - timedelta(hours=24)).fetch(None)

		page_value = {
				'list': garbage_list
		}

		for i in garbage_list:
			box_instance = CovertBox.query(CovertBox.blob_key == i.key()).get()

			try:
				box_instance.key.delete()
			except AttributeError:
				pass

			i.delete()

		box_query = CovertBox.query(filters=CovertBox.expiry_date > datetime.now())
		box_list = box_query.fetch()

		page_value = {
				'list': box_list 
		}

		page = JINJA_ENVIRONMENT.get_template('pages/gf.html')
		self.response.out.write(page.render(page_value))

application = webapp2.WSGIApplication([
	('/', MainHandler),
	('/error', ErrorHandler),
	('/upload', UploadHandler),
	('/opening', DownloadHandler),
	('/opened', DownloadHandler),
	('/open/([^/]+)?', ServeHandler),
	('/trash/([^/]+)?', DeleteHandler),
	('/gf', GarbageFlushHandler),
	], debug=True)

