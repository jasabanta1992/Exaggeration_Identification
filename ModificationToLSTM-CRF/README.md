## Original Code

The original code is an implementation that can be found at http://arxiv.org/abs/1603.01360


## Initial setup

To use the tagger, you need Python 2.7, with Numpy and Theano installed.


## Tag sentences

```
./tagger2.py --model models/english/ --input input.txt --output output.txt
```


## Train a model

To train the model, you need to use the train.py script and provide the location of the training, development and testing set:

```
./train2.py --train train.txt --dev dev.txt --test test.txt
```

The training script will automatically give a name to the model and store it in ./models/
There are many parameters you can tune (CRF, dropout rate, embedding dimension, LSTM hidden layer size, etc). To see all parameters, simply run:

```
./train.py --help
```
