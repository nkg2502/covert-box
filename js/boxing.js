$('#normal_button')[0].onclick = function() {
	$('#user_key_input')[0].type = 'password';
	$('#user_key_input')[0].value = '';
	$('#email_input')[0].type = 'hidden';
};

$('#secure_button')[0].onclick = function() {
	$('#user_key_input')[0].type = 'hidden';
	$('#email_input')[0].type = 'email';
	$('#email_input')[0].value = '';
};

