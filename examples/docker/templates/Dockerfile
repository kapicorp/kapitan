FROM {{image}}
COPY target/blah.jar /app/blah.jar
{% if 'web' == name %}
EXPOSE ${PORT}
{% endif %}
ENTRYPOINT ["java", "-jar", "/app/blah.jar"]
