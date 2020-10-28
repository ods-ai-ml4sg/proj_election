## proj_election: video analysis

Solution based on FairMOT project: [repo](https://github.com/ifzhang/FairMOT) and [paper](https://arxiv.org/abs/2004.01888)


### Environment setup
```sh
python3 -m venv venv
source venv/bin/activate
cd proj_election/video_voters_amount/
pip install cython==0.29.21
pip install -r requirements.txt
```
* As in the FairMot paper we use [DCNv2](https://github.com/CharlesShang/DCNv2) in our backbone network.
```sh
git clone https://github.com/lbin/DCNv2.git
cd DCNv2
git checkout pytorch_1.6
./make.sh
cd ..
```
Pretrained model can be downloaded from here [fairmot_dla34.pth](https://drive.google.com/file/d/1iqRQjsG9BawIl8SlFomMg5iwkb6nqSpi/view?usp=sharing)
Put it in the "models/" directory 

### Download 2012 President Election Data
```sh
cd data/2012_President_elections/
head -n 10 youtube_links.txt | while read line 
do
   youtube-dl $line
done
```

### Demo people tracking
```sh
cd data/2012_President_elections/
ffmpeg -i "УИК 577 камера №1 2012-03-04_UTC_15-00.mp4-4tstsZuA0XQ.mkv" -ss 00:09:30 -to 00:10:30 -c copy sample.mp4
cd ../../src
python demo.py mot \
    --load_model ../models/fairmot_dla34.pth \
    --input-video ../data/2012_President_elections/sample.mp4
```
result can be found in file data/result.mp4
