
service rabbitmq-server start
rabbitmq-plugins enable rabbitmq_management

service nginx start

service supervisor stop
service supervisor start

supervisorctl start all