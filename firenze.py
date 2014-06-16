'''
	firenze prototype
'''
import os
import urllib

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

import webapp2
import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(
		loader = jinja2.FileSystemLoader(os.path.dirname(__file__)),
		extensions = ['jinja2.ext.autoescape'],
		autoescape = True)

class MainHandler(webapp2.RequestHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/upload')

		index_page = JINJA_ENVIRONMENT.get_template('index.html')

		self.response.out.write(index_page.render({'upload_url': upload_url}))

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
	def post(self):
		upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
		self.redirect('/done')

class DoneHandler(webapp2.RequestHandler):
	def get(self):
		done_page = JINJA_ENVIRONMENT.get_template('done.html')
		self.response.out.write(done_page.render({}))

application = webapp2.WSGIApplication([('/', MainHandler),
	('/upload', UploadHandler),
	('/done', DoneHandler)],
	debug=True)
