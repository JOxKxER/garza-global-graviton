FROM ubuntu:22.04
COPY crunch_task.sh /golem/work/crunch_task.sh
RUN chmod +x /golem/work/crunch_task.sh