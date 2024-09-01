FROM amazoncorretto:11
COPY target/blah.jar /app/blah.jar
EXPOSE ${PORT}
ENTRYPOINT ["java", "-jar", "/app/blah.jar"]