import numpy as np
import pandas as pd
import os
import sys
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.model_selection import train_test_split
import tensorflow as tf
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import keras

from keras.models import Sequential
from keras.layers import Dense, Conv2D , MaxPool2D , Flatten , Dropout , BatchNormalization
from keras.preprocessing.image import ImageDataGenerator
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report,confusion_matrix
from keras.callbacks import ReduceLROnPlateau
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelBinarizer

sys.path.append('.')
from scripts.Data import *

# Modele ensembliste
def experience2():

    # data import
    train_df = pd.read_csv("./data/raw/sign_mnist_train.csv")
    old_test_df = pd.read_csv("./data/raw/old_sign_mnist_test.csv")
    test_df = pd.read_csv("./data/raw/test.csv")
    
    
    m1_train_df = train_df.copy()
    m1_val_df = old_test_df.copy()
    
    # Data manipulation
    m1_y_train = m1_train_df['label']
    m1_y_val = m1_val_df['label']


    # label
    label_binarizer = LabelBinarizer()
    #
    m1_y_train = label_binarizer.fit_transform(m1_y_train)
    m1_y_val = label_binarizer.fit_transform(m1_y_val)

    # Normalization
    m1_X_train = m1_train_df.drop(columns=['label']).values/255
    m1_X_val = m1_val_df.drop(columns=['label']).values/255
    
    # Reshape
    m1_X_train = m1_X_train.reshape(-1,28,28,1)
    m1_X_val = m1_X_val.reshape(-1,28,28,1)

    

    # Data augmentation
    # Modele 1
    m1_datagen = ImageDataGenerator(
        featurewise_center=False,  # set input mean to 0 over the dataset
        samplewise_center=False,  # set each sample mean to 0
        featurewise_std_normalization=False,  # divide inputs by std of the dataset
        samplewise_std_normalization=False,  # divide each input by its std
        zca_whitening=False,  # apply ZCA whitening
        rotation_range=10,  # randomly rotate images in the range (degrees, 0 to 180)
        zoom_range = 0.1, # Randomly zoom image 
        width_shift_range=0.1,  # randomly shift images horizontally (fraction of total width)
        height_shift_range=0.1,  # randomly shift images vertically (fraction of total height)
        horizontal_flip=False,  # randomly flip images
        vertical_flip=False)  # randomly flip images  
    m1_datagen.fit(m1_X_train)
    
    learning_rate_reduction = ReduceLROnPlateau(monitor='val_accuracy', patience = 2, verbose=1, factor=0.5, min_lr=0.00001)
    
    # Modele de base
    model = Sequential()
    model.add(Conv2D(75 , (3,3) , strides = 1 , padding = 'same' , activation = 'relu' , input_shape = (28,28,1)))
    model.add(BatchNormalization())
    model.add(MaxPool2D((2,2) , strides = 2 , padding = 'same'))
    model.add(Conv2D(50 , (3,3) , strides = 1 , padding = 'same' , activation = 'relu'))
    model.add(Dropout(0.2))
    model.add(BatchNormalization())
    model.add(MaxPool2D((2,2) , strides = 2 , padding = 'same'))
    model.add(Conv2D(25 , (3,3) , strides = 1 , padding = 'same' , activation = 'relu'))
    model.add(BatchNormalization())
    model.add(MaxPool2D((2,2) , strides = 2 , padding = 'same'))
    model.add(Flatten())
    model.add(Dense(units = 512 , activation = 'relu'))
    model.add(Dropout(0.3))
    model.add(Dense(units = 24 , activation = 'softmax'))
    model.compile(optimizer = 'adam' , loss = 'categorical_crossentropy' , metrics = ['accuracy'])
    
    
    m1_model = tf.keras.models.clone_model(model)
    m1_model.compile(optimizer = 'adam' , loss = 'categorical_crossentropy' , metrics = ['accuracy'])
    
    epochs = 20
    weights_path = os.path.join('.','data','weights',f'model_weights_{epochs}.h5')
    if not os.path.exists(weights_path):
        m1_history = m1_model.fit(
                    m1_datagen.flow(m1_X_train, m1_y_train, batch_size = 128),
                    epochs = epochs,
                    validation_data=(m1_X_val, m1_y_val),
                    callbacks=[learning_rate_reduction]
                    )
        m1_model.save_weights(weights_path)
    else:
        m1_model.load_weights(weights_path)
        
        
     # Splitting columns A1 to A784 into a separate DataFrame
    df_A = test_df.filter(like='pixel_a')
    test_A = df_A.values.reshape(-1,28,28,1)
    y_pred_A = np.argmax(m1_model.predict(test_A), axis=1)
    y_pred_A[y_pred_A >= 9] +=  1
    
    # Splitting columns B1 to B784 into a separate DataFrame
    df_B = test_df.filter(like='pixel_b')
    test_B = df_B.values.reshape(-1,28,28,1)
    y_pred_B = np.argmax(m1_model.predict(test_B),axis=1)
    y_pred_B[y_pred_B >= 9] +=  1    
    
    def label_to_uppercase(index):
        return chr(index + 65)  # 'A' is ASCII 65

    # Normalize ASCII sum
    def normalize_ascii_sum(ascii_sum):
        while ascii_sum > 122:  # 'z' is ASCII 122
            ascii_sum -= 65  # 122 ('z') - 65 ('A') + 1
        return ascii_sum

    # Convert predictions to uppercase letters and then to ASCII
    ascii_predictions_a = [ord(label_to_uppercase(p)) for p in y_pred_A]
    ascii_predictions_b = [ord(label_to_uppercase(p)) for p in y_pred_B]

    # Sum and normalize ASCII values
    ascii_sums = [normalize_ascii_sum(a + b) for a, b in zip(ascii_predictions_a, ascii_predictions_b)]

    # Convert sums to characters
    transformed_labels = [chr(ascii_sum) for ascii_sum in ascii_sums]
    
    #transformed_labels = [transform_labels(label_A, label_B) for label_A, label_B in zip(y_pred_A,y_pred_B)]
    IDS = np.arange(len(transformed_labels))
    res = pd.DataFrame(data={"id":IDS, 'label':transformed_labels})

    prediction_path = os.path.join('data','prediction','cnn_1.csv')
    print(np.unique(res['label'], return_counts=True))
    res.to_csv(prediction_path, index=False)

experience2()
