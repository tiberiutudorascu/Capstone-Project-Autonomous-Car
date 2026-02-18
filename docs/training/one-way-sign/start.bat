dir /b /s n\*.jpg > neg.txt

mkdir data

opencv_createsamples.exe -img semn1.png -bg neg.txt -info info.txt -num 2500 -maxxangle 0.5 -maxyangle 0.5 -maxzangle 0.5 -w 32 -h 32 -vec pos1.vec

opencv_createsamples.exe -img semn2.png -bg neg.txt -info info.txt -num 2500 -maxxangle 0.5 -maxyangle 0.5 -maxzangle 0.5 -w 32 -h 32 -vec pos2.vec

opencv_createsamples.exe -img semn3.png -bg neg.txt -info info.txt -num 2500 -maxxangle 0.5 -maxyangle 0.5 -maxzangle 0.5 -w 32 -h 32 -vec pos3.vec

python3 vec-files-merge.py

opencv_traincascade.exe ^
-data data ^
-vec positives.vec ^
-bg neg.txt ^
-numPos 5000 ^
-numNeg 2000 ^
-numStages 20 ^
-w 32 -h 32 ^
-featureType LBP ^
-minHitRate 0.999 ^
-maxFalseAlarmRate 0.4 ^
-precalcValBufSize 4096 ^
-precalcIdxBufSize 4096