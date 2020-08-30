import numpy as np
import tensorflow as tf
import random
import os
import pickle

class SkipGram(tf.keras.Model):
    def __init__(self, config):
        super(SkipGram, self).__init__()
        self.embedding = None
        self.vocab_size = config["vocab_size"]
        self.embedding_dim = config["embedding_dim"]
        self.optimizer = tf.keras.optimizers.Adadelta(config["learning_rate"])

    def initEmbedding(self):
        print("initialize model...")
        self.embedding = tf.Variable(tf.random.normal([self.vocab_size, self.embedding_dim], 0, 0.01))

def train_skipgram(output_path, patient_record_path, concept2id_path, epochs, batch_size, learning_rate=0.001, embedding_dim=128):

    config = locals().copy()

    print("load data...")
    recs = load_data(patient_record_path)
    concept2id = load_data(concept2id_path)
    config["vocab_size"] = len(concept2id)

    print("build and initialize model...")
    skipgram = SkipGram(config)
    skipgram.initEmbedding()

    print("start training...")
    num_batches = int(np.ceil(len(recs) / batch_size))

    for epoch in range(epochs):
        cost_record = []
        progbar = tf.keras.utils.Progbar(num_batches)

        for i in random.sample(range(num_batches), num_batches): # shuffling the data 
            batch_rec = recs[batch_size*i:batch_size*(i+1)]
            i_batch, j_batch = prepare_batch(batch_rec)

            with tf.GradientTape() as tape:
                batch_cost = computeEmbCost(skipgram, i_batch, j_batch)
                gradients = tape.gradient(batch_cost, skipgram.trainable_variables)
                skipgram.optimizer.apply_gradients(zip(gradients, skipgram.trainable_variables))

            cost_record.append(batch_cost.numpy())
            progbar.add(1)

        print('epoch:{e}, mean loss:{l:.6f}'.format(e=epoch+1, l=np.mean(cost_record)))

    print("save trained embeddings...")
    np.save(os.path.join(output_path, 
    "skipgram_embeddings_e{}_loss{:.4f}.npy".format(epochs, np.mean(cost_record))), skipgram.embedding.numpy()) 

def computeEmbCost(model, i_vec, j_vec): 
    logEps = tf.constant(1e-8)
    norms = tf.reduce_sum(tf.math.exp(tf.matmul(model.embedding, model.embedding, transpose_b=True)), axis=1)
    denoms = tf.math.exp(tf.reduce_sum(tf.multiply(tf.nn.embedding_lookup(model.embedding, i_vec), 
        tf.nn.embedding_lookup(model.embedding, j_vec)), axis=1))
    concept_cost = tf.negative(tf.math.log((tf.divide(denoms, tf.gather(norms, i_vec)) + logEps)))
    return tf.math.reduce_mean(concept_cost)

def prepare_batch(record):
    i_vec = []
    j_vec = []

    for visit in record:
        pick_two(visit, i_vec, j_vec)

    return np.array(i_vec).astype("int32"), np.array(j_vec).astype("int32")

def pick_two(visit, i_vec, j_vec):
    for first in visit:
        for second in visit:
            if first == second: 
                continue
            i_vec.append(first)
            j_vec.append(second)

    return i_vec, j_vec

def load_data(data_path):
    my_data = pickle.load(open(data_path, 'rb'))

    return my_data