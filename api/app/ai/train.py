import dataset
import tensorflow as tf
import time
from datetime import timedelta
import math
import random
import numpy as np

# Adding seed so that random initialization is consistent
from numpy.random import seed
seed(1)
from tensorflow import set_random_seed
set_random_seed(2)


batch_size = 32

# Prepare input data
classes = ['healthy','deficiency','powdery','burn']
num_classes = len(classes)

# 20% of the data will be used for validation
validation_size = 0.2
img_size = 128
num_channels = 3
train_path='./data/train/'
check_point_name = './canapest-multi-model'

# Load training and validation images and labels
data = dataset.read_train_sets(train_path, img_size, classes, validation_size=validation_size)


print("Complete reading input data. Will Now print a snippet of it")
print("Number of files in Training-set:\t\t{}".format(len(data.train.labels)))
print("Number of files in Validation-set:\t{}".format(len(data.valid.labels)))



session = tf.Session()
x = tf.placeholder(tf.float32, shape=[None, img_size,img_size,num_channels], name='x')

# Labels
y_true = tf.placeholder(tf.float32, shape=[None, num_classes], name='y_true')
y_true_cls = tf.argmax(y_true, dimension=1)
#keep_prob = tf.placeholder(tf.float32)



# Network graph params

filter_size_conv1 = 3
num_filters_conv1 = 32

filter_size_conv2 = 3
num_filters_conv2 = 32

filter_size_conv3 = 3
num_filters_conv3 = 64

fc_layer_size = 128

def create_weights(shape):
    return tf.Variable(tf.truncated_normal(shape, stddev=0.05))


def create_biases(size):
    return tf.Variable(tf.constant(0.05, shape=[size]))


def create_convolutional_layer(input, num_input_channels, conv_filter_size, num_filters):
    '''Create a convolutional layer + max pool + relu activation'''

    # Trainable weights and biases
    weights = create_weights(shape=[conv_filter_size, conv_filter_size, num_input_channels, num_filters])
    biases = create_biases(num_filters)

    # Create the convolutional layer
    layer = tf.nn.conv2d(input=input, filter=weights, strides=[1, 1, 1, 1], padding='SAME')
    layer += biases

    # Max-pooling.
    layer = tf.nn.max_pool(value=layer, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

    # Relu activation function
    layer = tf.nn.relu(layer)

    return layer


def create_flatten_layer(layer):
    '''Flatten layer of dimension  [batch_size img_size img_size num_channels] to single column tensor'''

    layer_shape = layer.get_shape()
    num_features = layer_shape[1:4].num_elements()

    # Flatten layer reshaped to num_features
    layer = tf.reshape(layer, [-1, num_features])

    return layer


def create_fc_layer(input, num_inputs, num_outputs, use_relu=True):
    '''Create fully connected layer'''

    #Trainable weights and biases
    weights = create_weights(shape=[num_inputs, num_outputs])
    biases = create_biases(num_outputs)

    # Fully connected layer takes input x and produces wx+b
    layer = tf.matmul(input, weights) + biases
    #layer = tf.nn.dropout(layer,keep_prob)

    if use_relu:
        layer = tf.nn.relu(layer)

    return layer



# Netwok graph

layer_conv1 = create_convolutional_layer(input=x,
               num_input_channels=num_channels,
               conv_filter_size=filter_size_conv1,
               num_filters=num_filters_conv1)

layer_conv2 = create_convolutional_layer(input=layer_conv1,
               num_input_channels=num_filters_conv1,
               conv_filter_size=filter_size_conv2,
               num_filters=num_filters_conv2)

layer_conv3= create_convolutional_layer(input=layer_conv2,
               num_input_channels=num_filters_conv2,
               conv_filter_size=filter_size_conv3,
               num_filters=num_filters_conv3)

layer_flat = create_flatten_layer(layer_conv3)

layer_fc1 = create_fc_layer(input=layer_flat,
                     num_inputs=layer_flat.get_shape()[1:4].num_elements(),
                     num_outputs=fc_layer_size,
                     use_relu=True)

layer_fc2 = create_fc_layer(input=layer_fc1,
                     num_inputs=fc_layer_size,
                     num_outputs=num_classes,
                     use_relu=False)

y_pred = tf.nn.softmax(layer_fc2,name='y_pred')
y_pred_cls = tf.argmax(y_pred, dimension=1)

session.run(tf.global_variables_initializer())


# Training functions
cross_entropy = tf.nn.softmax_cross_entropy_with_logits(logits=layer_fc2, labels=y_true)
cost = tf.reduce_mean(cross_entropy)
optimizer = tf.train.AdamOptimizer(learning_rate=1e-4).minimize(cost)
correct_prediction = tf.equal(y_pred_cls, y_true_cls)
accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))


session.run(tf.global_variables_initializer())


def show_progress(epoch, feed_dict_train, feed_dict_validate, val_loss):
    '''Show progress while training'''
    EARLY_STOP = 0.85
    acc = session.run(accuracy, feed_dict=feed_dict_train)
    val_acc = session.run(accuracy, feed_dict=feed_dict_validate)
    msg = "Training Epoch {0} --- Training Accuracy: {1:>6.1%}, Validation Accuracy: {2:>6.1%},  Validation Loss: {3:.3f}"
    print(msg.format(epoch + 1, acc, val_acc, val_loss))
    return val_acc > EARLY_STOP


total_iterations = 0

saver = tf.train.Saver()
def train(num_iteration):
    '''Training loop'''

    global total_iterations

    for i in range(total_iterations, total_iterations + num_iteration):

        # Fecth batch
        x_batch, y_true_batch, _, _ = data.train.next_batch(batch_size)
        x_valid_batch, y_valid_batch, _, _ = data.valid.next_batch(batch_size)


        feed_dict_tr = {x: x_batch, y_true: y_true_batch}
        feed_dict_val = {x: x_valid_batch, y_true: y_valid_batch}

        session.run(optimizer, feed_dict=feed_dict_tr)

        # Show progress and save learnt parameters
        if i % int(data.train.num_examples/batch_size) == 0:
            val_loss = session.run(cost, feed_dict=feed_dict_val)
            epoch = int(i / int(data.train.num_examples/batch_size))

            early_stop = show_progress(epoch, feed_dict_tr, feed_dict_val, val_loss)
            saver.save(session, check_point_name)
	    if early_stop:
		return 0


    total_iterations += num_iteration

train(num_iteration=3000)
