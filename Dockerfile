FROM python:3.6.6

WORKDIR /usr/src/app

COPY Requirements.txt ./
RUN pip install --no-cache-dir -r Requirements.txt
RUN pip3 install http://download.pytorch.org/whl/cpu/torch-0.4.1-cp36-cp36m-linux_x86_64.whl
RUN pip3 install torchvision

COPY each/ ./each/
COPY swagger-ui/ ./swagger-ui/

COPY server.py 		./server.py
COPY config.json 	./config.json
COPY swagger.json 	./swagger.json
COPY VERSION 		./VERSION
COPY museum.json        ./museum.json
COPY feed.json          ./feed.json
COPY client_config.json ./client_config.json
COPY startup.sh         ./startup.sh
RUN chmod 777 ./startup.sh && \
    sed -i 's/\r//' ./startup.sh

RUN mkdir -p ./logs
RUN chmod 777 ./logs
VOLUME ./logs

RUN mkdir -p ./images
RUN chmod 777 ./images
VOLUME ./images

EXPOSE 4201

CMD ["./startup.sh"]
