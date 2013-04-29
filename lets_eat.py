from itty import get,put,post,run_itty

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

users = {
	"bbaldino@gmail.com" : "Brian",
	"neil.joshi@gmail.com"  : "Neil",
	"sharath.ramegowda@yahoo.com" : "Sharath"
}

local_email = "lets.go.eat.now@gmail.com"

index_template = \
'''
<html>
	<head>
		<script>
			function get_selected_user() {
				var e = document.getElementById("users");
				return e.options[e.selectedIndex].value;
			}

			function submit_request() {
				user=get_selected_user();
				url='/api/group_requests';
				data = "originator="+user
				xmlhttp = new XMLHttpRequest();
				xmlhttp.open("POST", url);
				xmlhttp.setRequestHeader("Content-type","application/x-www-form-urlencoded");
				xmlhttp.onreadystatechange = function() {
					if (xmlhttp.readyState==4 && xmlhttp.status==200) {
						document.getElementById("result").innerHTML=xmlhttp.responseText;
					}
				}
				xmlhttp.send(data);
			}
		</script>
	</head>
	<body>
		<p>Let's Eat!</p>
		I am ... <select id="users">
			%s
		</select>
		<br/>
		<button onclick="submit_request()">Ready!</button>
		<br/>
		<div id="result"></div>
	</body>
</html>
'''

request_result_template = \
'''
%s
'''

response_email_template = \
'''
<html>
	<head>
	</head>
	<body>
		Hi %s. %s has initiated a lunch request. Visit 
		<a href="%s"> here </a> to send a response.
	</body>
</html>

'''

response_template = \
'''
<html>
	<head>
		<script>
			function send_response(id) {
				
				var url='/api/group_request/1';
				var xmlhttp = new XMLHttpRequest();
				xmlhttp.open("POST", url);
				xmlhttp.setRequestHeader("Content-type","application/x-www-form-urlencoded");
				xmlhttp.send("email=%s&response="+id);
			}
		</script>
	</head>
	<body>
		<span><button id="yes" onclick="send_response(this.id)">Yes</button></span>
		<span><button id="no" onclick="send_response(this.id)">No</button></span>
	</body>
</html>
'''

request_complete_email_template = \
'''
<html>
	<body>
		<table>
			<tr>
				<th>Yes</th>
				<th>No</th>
			</tr>
			%s
		</table>
	</body>
</html>
'''

def build_option_values():
	option_value="<option value=\"%s\">%s</option>"
	option_values=""
	for email,name in users.iteritems():
		option_values += option_value % (email,name) + '\n'

	return option_values

from itertools import izip_longest
def build_response_table(state_map):
	table_rows=""
	table_row="<tr><td>%s</td><td>%s</td></tr>"
	part_list=lambda resp : [users[email] for email,status in state_map.iteritems() if status==resp]
	for yes,no in izip_longest(part_list("yes"),part_list("no"),fillvalue=""):
		table_rows+=table_row%(yes,no)
	return table_rows

group_request=None

def send_email_notification(email,subject,message):

	#print email,message

	# Create message container - the correct MIME type is multipart/alternative.
	msg = MIMEMultipart('alternative')
	msg['Subject'] = subject
	msg['From'] = local_email

	# Create the body of the message (a plain-text and an HTML version).
	text = ""
	
	# Record the MIME types of both parts - text/plain and text/html.
	part1 = MIMEText(text, 'plain')
	part2 = MIMEText(message, 'html')

	# Attach parts into message container.
	# According to RFC 2046, the last part of a multipart message, in this case
	# the HTML message, is best and preferred.
	msg.attach(part1)
	msg.attach(part2)

	username = "lets.go.eat.now@gmail.com"
	password = "northernpike"

	# Send the message via local SMTP server.
	s = smtplib.SMTP('smtp.gmail.com:587')
	s.starttls()
	s.login(username,password)
			
	msg['To'] = email		
	# sendmail function takes 3 arguments: sender's address, recipient's address
	# and message to send - here it is sent as one string.
	s.sendmail(local_email, email, msg.as_string())
	
	s.quit()

class GroupRequest(object):
	def __init__(self,originator):
		self.originator = originator
		self.part_state = self.create_state_map(users.iterkeys())
		self.part_state[originator] = "yes"

	def create_state_map(self,participants):
		state_map = {}
		for p in participants:
			state_map[p] = "pending"
		return state_map

	def handle_response(self,email,response):
		if email in self.part_state:
			print "email:",email,"response:",response
			self.part_state[email] = response

	def check_status(self):
		if all([x != "pending" for x in self.part_state.itervalues()]):
			message=request_complete_email_template%build_response_table(self.part_state)
			for email in self.part_state.iterkeys():
				send_email_notification(email,"Request Status",message)
			return True

		return False

	def send_notifications_to_pending(self):
		subject = "Lunch Request"
		for email,state in self.part_state.iteritems():
			if state == "pending":
				link = "http://10.154.136.15:8080/response?email=%s"%email
				msg=response_email_template % (users[email],users[self.originator],link)
				send_email_notification(email,subject,msg)

@get('/')
def request_page(request):
	return index_template % build_option_values()

@get('/response')
def response_page(request):
	email=request.GET.get("email")
	
	return response_template % email

@post('/api/group_requests')
def create_group_request(request):
	originator = request.POST.get("originator")
	global group_request
	
	if group_request:
		return request_result_template % "Request Already In Progress"
	
	group_request = GroupRequest(originator)
	group_request.send_notifications_to_pending()
	return request_result_template % "Request Successfully Created"

@post('/api/group_request/1')
def update_group_request(request):
	global group_request
	email = request.POST.get("email")
	response = request.POST.get("response")
	if group_request:
		group_request.handle_response(email,response)

		if group_request.check_status():
			group_request = None

	return ""


def main():
	run_itty(host="0.0.0.0",port=8080)

if __name__ == "__main__":
	main()

