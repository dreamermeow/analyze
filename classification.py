# в этом варианте только шторм/не шторм
import numpy as np
import pandas as pd
import keras
from keras import layers
from keras.optimizers import Adam
from sklearn.metrics import confusion_matrix
import tensorflow as tf


df = pd.read_excel('data1116.xlsx', engine='openpyxl')
for column in df.columns:
    df[column] = df[column].apply(lambda x: float(x.replace(',', '.')) if isinstance(x, str) else x)
df = df.astype(float)

# признаки и метки
features = df.iloc[:, 3:32].values
dst_index = df.iloc[:, 24].values
shtorm = np.where(dst_index < -50, 1, 0)

# разделение данных
num_val_samples = int(len(features) * 0.2)
train_X, val_X = features[:-num_val_samples], features[-num_val_samples:]
train_y, val_y = shtorm[:-num_val_samples], shtorm[-num_val_samples:]

# проверка на отсутсвие данных  

if np.isnan(train_X).sum() > 0 or np.isnan(val_X).sum() > 0:
    print(" Найдены NaN. Замена  на средние значения.")
    train_X = np.nan_to_num(train_X, nan=np.nanmean(train_X))
    val_X = np.nan_to_num(val_X, nan=np.nanmean(train_X))

# баланс классов

unique, counts = np.unique(train_y, return_counts=True)
class_weights = {0: counts[1] / (counts[0] + counts[1]), 1: (counts[0] / (counts[0] + counts[1])) * 2.5}  
# нормализация

mean, std = np.mean(train_X, axis=0), np.std(train_X, axis=0)
std[std == 0] = 1
train_X = (train_X - mean) / std
val_X = (val_X - mean) / std


model = keras.Sequential([
    layers.Input(shape=train_X.shape[1:]),
    layers.Dense(512, activation="relu", kernel_initializer='he_normal', kernel_regularizer=keras.regularizers.l1_l2(l1=0.0005, l2=0.001)),
    layers.BatchNormalization(),
    layers.Dropout(0.1),  
    layers.Dense(256, activation="relu", kernel_regularizer=keras.regularizers.l2(0.001)),
    layers.BatchNormalization(),
    layers.Dropout(0.2),  
    layers.Dense(128, activation="relu", kernel_regularizer=keras.regularizers.l2(0.001)),
    layers.BatchNormalization(),
    layers.Dense(64, activation="relu", kernel_regularizer=keras.regularizers.l2(0.001)),
    layers.BatchNormalization(),
    layers.Dense(32, activation="relu", kernel_regularizer=keras.regularizers.l2(0.001)),
    layers.BatchNormalization(),
    layers.Dense(1, activation="sigmoid"),  
])


model.compile(
    optimizer=Adam(learning_rate=1e-3),
    loss="binary_crossentropy",
    metrics=["accuracy", keras.metrics.Recall(), keras.metrics.Precision()]
)


cosine_annealing = keras.callbacks.LearningRateScheduler(lambda epoch: 1e-3 * (0.5 * (1 + np.cos(np.pi * epoch / 50))))
early_stopping = keras.callbacks.EarlyStopping(monitor='val_loss', patience=7, restore_best_weights=True)
model.fit(
    train_X, train_y,
    batch_size=128,
    epochs=50,
    validation_data=(val_X, val_y),
    class_weight=class_weights,
    callbacks=[cosine_annealing, early_stopping],
    verbose=2
)


probs = model.predict(val_X).flatten()
predictions = (probs > 0.5).astype("uint8")  


tn, fp, fn, tp = confusion_matrix(val_y, predictions, labels=[0, 1]).ravel()
print("Правильно предсказанные штормы True Positives",tp)
print("Штормы, которые не были предсказаны False Negatives",fn)
print("Не штормы, но предсказаны как штормы False Positives",fp)
print("Правильно предсказанные не штормы True Negatives",tn)