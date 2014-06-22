'''
	firenze prototype
'''
import os
import urllib
import hashlib
import uuid

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
	key = ndb.BlobKeyProperty()
	file_name = ndb.StringProperty()

class MainHandler(webapp2.RequestHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/upload')

		index_page = JINJA_ENVIRONMENT.get_template('index.html')

		self.response.out.write(index_page.render({'upload_url': upload_url}))

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
	def post(self):
		upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
		user_key = self.request.get('user_key')
		email = self.request.get('email')
		
		retrieval_key = None

		# email address validation
		if '' != email:
			retrieval_key = hashlib.sha512(str(uuid.uuid4().get_hex()) + email).hexdigest()

			message = mail.EmailMessage(
					sender="? Covert-Box ?<covert-box@appspot.gserviceaccount.com>",
					subject='"{}" has been uploaded'.format(upload_files[0].filename))

			message.to = "<" + email + ">"
			message.body = """Dear You,
retrieval key: {}
? Covert-Box ?
""".format(retrieval_key)

			message.send()

		elif '' != user_key: # user_key validation
			retrieval_key = user_key

		box_instance = CovertBox(parent=ndb.Key('retrieval_key', str(retrieval_key)))

		box_instance.key = upload_files[0].key()
		box_instance.file_name = upload_files[0].filename

		box_instance.put()

		self.redirect('/done')

class DoneHandler(webapp2.RequestHandler):
	def get(self):
		done_page = JINJA_ENVIRONMENT.get_template('done.html')


		self.response.out.write(done_page.render({}))

class DownloadHandler(webapp2.RequestHandler):
	def get(self):
		page = JINJA_ENVIRONMENT.get_template('gate.html')
		self.response.out.write(page.render({}))

	def post(self):
		page = JINJA_ENVIRONMENT.get_template('download.html')

		user_key = self.request.get('user_key')

		box_query = CovertBox.query(ancestor=ndb.Key('retrieval_key', user_key))
		box_list = box_query.fetch()

		page_value = {
				'list': box_list 
		}

		self.response.out.write(page.render(page_value))


class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
	def get(self, resource):
		resource = str(urllib.unquote(resource))
		blob_info = blobstore.BlobInfo.get(resource)
		self.send_blob(blob_info, save_as=blob_info.filename)

application = webapp2.WSGIApplication([('/', MainHandler),
	('/upload', UploadHandler),
	('/done', DoneHandler),
	('/download', DownloadHandler),
	('/covert_room', DownloadHandler),
	('/serve/([^/]+)?', ServeHandler),
	], debug=True)
