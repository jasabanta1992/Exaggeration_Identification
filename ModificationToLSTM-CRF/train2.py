#!/usr/bin/env python

import os
import numpy as np
import optparse
import itertools
from collections import OrderedDict
from utils2 import create_input
import loader

from utils2 import models_path, evaluate, eval_script, eval_temp
from loader2 import word_mapping, char_mapping, tag_mapping, postag_mapping, word_bigram_mapping, pos_bigram_mapping
from loader2 import update_tag_scheme, prepare_dataset, to_leximes
from loader2 import augment_with_pretrained
from model2 import Model

# Read parameters from command line
optparser = optparse.OptionParser()
optparser.add_option(
    "-T", "--train", default="",
    help="Train set location"
)
optparser.add_option(
    "-d", "--dev", default="",
    help="Dev set location"
)
optparser.add_option(
    "-t", "--test", default="",
    help="Test set location"
)
optparser.add_option(
    "-s", "--tag_scheme", default="iob",
    help="Tagging scheme (IOB or IOBES)"
)
optparser.add_option(
    "-l", "--lower", default="0",
    type='int', help="Lowercase words (this will not affect character inputs)"
)
optparser.add_option(
    "-z", "--zeros", default="0",
    type='int', help="Replace digits with 0"
)
optparser.add_option(
    "-c", "--char_dim", default="25",
    type='int', help="Char embedding dimension"
)
optparser.add_option(
    "-C", "--char_lstm_dim", default="25",
    type='int', help="Char LSTM hidden layer size"
)
optparser.add_option(
    "-b", "--char_bidirect", default="1",
    type='int', help="Use a bidirectional LSTM for chars"
)
optparser.add_option(
    "-w", "--word_dim", default="100",
    type='int', help="Token embedding dimension"
)
optparser.add_option(
    "-W", "--word_lstm_dim", default="100",
    type='int', help="Token LSTM hidden layer size"
)
optparser.add_option(
    "-B", "--word_bidirect", default="1",
    type='int', help="Use a bidirectional LSTM for words"
)
optparser.add_option(
    "-p", "--pre_emb", default="",
    help="Location of pretrained embeddings"
)
optparser.add_option(
    "-A", "--all_emb", default="0",
    type='int', help="Load all embeddings"
)
optparser.add_option(
    "-a", "--cap_dim", default="0",
    type='int', help="Capitalization feature dimension (0 to disable)"
)
optparser.add_option(
    "-f", "--crf", default="1",
    type='int', help="Use CRF (0 to disable)"
)
optparser.add_option(
    "-D", "--dropout", default="0.5",
    type='float', help="Droupout on the input (0 = no dropout)"
)
optparser.add_option(
    "-L", "--lr_method", default="sgd-lr_.005",
    help="Learning method (SGD, Adadelta, Adam..)"
)
optparser.add_option(
    "-r", "--reload", default="0",
    type='int', help="Reload the last saved model"
)
optparser.add_option(
    "-P", "--postag_dim", default="40",
    type='int', help="include pos tag feature"
)

optparser.add_option(
    "-E", "--wordbigram_dim", default="0",
    type='int', help="include word bigram dimension"
)

optparser.add_option(
    "-G", "--word_lexim", default="0",
    type='int', help="include word lexims dimension"
)

optparser.add_option(
    "-H", "--posbigram_dim", default="40",
    type='int', help="include pos bigram dimension"
)


optparser.add_option(
    "-I", "--wordnet_cluster", default="0",
    type='int', help="Number of wordnet clusters dimension"
)

opts = optparser.parse_args()[0]

# Parse parameters
parameters = OrderedDict()
parameters['tag_scheme'] = opts.tag_scheme
parameters['lower'] = opts.lower == 1
parameters['zeros'] = opts.zeros == 1
parameters['char_dim'] = opts.char_dim
parameters['char_lstm_dim'] = opts.char_lstm_dim
parameters['char_bidirect'] = opts.char_bidirect == 1
parameters['word_dim'] = opts.word_dim
parameters['word_lstm_dim'] = opts.word_lstm_dim
parameters['word_bidirect'] = opts.word_bidirect == 1
parameters['pre_emb'] = opts.pre_emb
parameters['all_emb'] = opts.all_emb == 1
parameters['cap_dim'] = opts.cap_dim
parameters['crf'] = opts.crf == 1
parameters['dropout'] = opts.dropout
parameters['lr_method'] = opts.lr_method
parameters['postag_dim'] = opts.postag_dim
parameters['wordbigram_dim'] = opts.wordbigram_dim
parameters['word_lexim'] = opts.word_lexim
parameters['posbigram_dim'] = opts.posbigram_dim
parameters['wordnet_cluster'] = opts.wordnet_cluster

# Check parameters validity
assert os.path.isfile(opts.train)
assert os.path.isfile(opts.dev)
assert os.path.isfile(opts.test)
assert parameters['char_dim'] > 0 or parameters['word_dim'] > 0
assert 0. <= parameters['dropout'] < 1.0
assert parameters['tag_scheme'] in ['iob', 'iobes']
assert not parameters['all_emb'] or parameters['pre_emb']
assert not parameters['pre_emb'] or parameters['word_dim'] > 0
assert not parameters['pre_emb'] or os.path.isfile(parameters['pre_emb'])

# Check evaluation script / folders
if not os.path.isfile(eval_script):
    raise Exception('CoNLL evaluation script not found at "%s"' % eval_script)
if not os.path.exists(eval_temp):
    os.makedirs(eval_temp)
if not os.path.exists(models_path):
    os.makedirs(models_path)

# Initialize model
model = Model(parameters=parameters, models_path=models_path)
print "Model location: %s" % model.model_path

# Data parameters
lower = parameters['lower']
zeros = parameters['zeros']
tag_scheme = parameters['tag_scheme']

# Load sentences
train_sentences = loader.load_sentences(opts.train, lower, zeros)

#for asent in train_sentences:
#	print '\n\n',asent
#	break
dev_sentences = loader.load_sentences(opts.dev, lower, zeros)
test_sentences = loader.load_sentences(opts.test, lower, zeros)




# Use selected tagging scheme (IOB / IOBES)
update_tag_scheme(train_sentences, tag_scheme)
update_tag_scheme(dev_sentences, tag_scheme)
update_tag_scheme(test_sentences, tag_scheme)


if (parameters['word_lexim']> 0):
	train_sentences = to_leximes(train_sentences)
	dev_sentences = to_leximes(dev_sentences)
	test_sentences = to_leximes(test_sentences)



#print train_sentences

#for asent in train_sentences:
#	print '\n\n',asent
#	break



# Create a dictionary / mapping of words
# If we use pretrained embeddings, we add them to the dictionary.
if parameters['pre_emb']:
    dico_words_train = word_mapping(train_sentences, lower)[0]
    dico_words, word_to_id, id_to_word = augment_with_pretrained(
        dico_words_train.copy(),
        parameters['pre_emb'],
        list(itertools.chain.from_iterable(
            [[w[0] for w in s] for s in dev_sentences + test_sentences])
        ) if not parameters['all_emb'] else None
    )
else:
    dico_words, word_to_id, id_to_word = word_mapping(train_sentences, lower)
    dico_words_train = dico_words

#print (dico_words_train)


#print len(dico_words_train), len(word_to_id), len(id_to_word)

#print id_to_word
	
# Create a dictionary and a mapping for words / POS tags / tags
dico_chars, char_to_id, id_to_char = char_mapping(train_sentences)
dico_tags, tag_to_id, id_to_tag = tag_mapping(train_sentences)

dico_postags, postag_to_id, id_to_postag = postag_mapping(train_sentences)
dico_wordbigrams, wordbigram_to_id, id_to_wordbigram = word_bigram_mapping(train_sentences, lower)
dico_posbigrams, posbigram_to_id, id_to_posbigram = pos_bigram_mapping(train_sentences, lower)
#print (wordbigram_to_id),'\n\n'#, (postag_to_id), (id_to_postag)




# Index data
train_data = prepare_dataset(
    train_sentences, word_to_id, char_to_id, tag_to_id, postag_to_id, wordbigram_to_id, posbigram_to_id, parameters['wordnet_cluster']  ,lower
)
dev_data = prepare_dataset(
    dev_sentences, word_to_id, char_to_id, tag_to_id, postag_to_id, wordbigram_to_id, posbigram_to_id,  parameters['wordnet_cluster'] ,lower
)
test_data = prepare_dataset(
    test_sentences, word_to_id, char_to_id, tag_to_id, postag_to_id, wordbigram_to_id, posbigram_to_id, parameters['wordnet_cluster'] ,lower
)


#for adata in train_data:
#	print adata
#	break


print "%i / %i / %i sentences in train / dev / test." % (
    len(train_data), len(dev_data), len(test_data))

# Save the mappings to disk
print 'Saving the mappings to disk...'
model.save_mappings(id_to_word, id_to_char, id_to_tag, id_to_postag, id_to_wordbigram,id_to_posbigram ,dico_tags)


# Build the model
f_train, f_eval = model.build(**parameters)



# Reload previous model values
if opts.reload:
    print 'Reloading previous model...'
    model.reload()

#
# Train network
#
singletons = set([word_to_id[k] for k, v
                  in dico_words_train.items() if v == 1])

n_epochs = 30  # number of epochs over the training set #JP Edit: from 100 to 20
freq_eval = len(train_data)  # evaluate on dev every freq_eval steps
best_dev = -np.inf
best_test = -np.inf
count = 0

for epoch in xrange(n_epochs):
    epoch_costs = []
    print "Starting epoch %i..." % epoch
    for i, index in enumerate(np.random.permutation(len(train_data))):
        count += 1
        input = create_input(train_data[index], parameters, True, singletons)
	#print input
	
        new_cost = f_train(*input)
	#print new_cost
        epoch_costs.append(new_cost)
        if i % 50 == 0 and i > 0 == 0:
            print "%i, cost average: %f" % (i, np.mean(epoch_costs[-50:]))
        if count % freq_eval == 0:
            dev_score = evaluate(parameters, f_eval, dev_sentences,
                                 dev_data, id_to_tag, dico_tags)
            test_score = evaluate(parameters, f_eval, test_sentences,
                                  test_data, id_to_tag, dico_tags)
            print "Score on dev: %.5f" % dev_score
            print "Score on test: %.5f" % test_score
            if dev_score > best_dev:
                best_dev = dev_score
                print "New best score on dev."
                
            if test_score > best_test:
                best_test = test_score
                print "New best score on test."
		print "Saving model to disk..."
                model.save()
    
    print "Epoch %i done. Average cost: %f" % (epoch, np.mean(epoch_costs))
    print "Till now obtained best score on dev: ", best_dev, " On test: ", best_test

