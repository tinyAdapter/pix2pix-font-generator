from __future__ import print_function, division
import scipy
from keras.datasets import mnist
from keras.layers import Input, Dense, Reshape, Flatten, Dropout, Concatenate
from keras.layers import BatchNormalization, Activation, ZeroPadding2D
from keras.layers.advanced_activations import LeakyReLU
from keras.layers.convolutional import UpSampling2D, Conv2D
from keras.models import Sequential, Model
from keras.optimizers import Adam
import datetime
import matplotlib.pyplot as plt
import sys
import numpy as np
import os


class Pix2Pix():
    def __init__(self):
        # Input shape
        self.img_rows = 64
        self.img_cols = 64
        self.channels = 1
        self.img_shape = (self.img_rows, self.img_cols, self.channels)

        # Configure data loader
        self.dataset_name = 'pix2pix_64'

        # Calculate output shape of D (PatchGAN)
        patch = int(self.img_rows / 2**4)
        self.disc_patch = (patch, patch, 1)

        # Number of filters in the first layer of G and D
        self.gf = 64
        self.df = 64

        optimizer = Adam(0.0002, 0.5)

        # Build and compile the discriminator
        self.discriminator = self.build_discriminator()
        self.discriminator.compile(loss='mse',
                                   optimizer=optimizer,
                                   metrics=['accuracy'])

        # -------------------------
        # Construct Computational
        #   Graph of Generator
        # -------------------------

        # Build the generator
        self.generator = self.build_generator()

        # Input images and their conditioning images
        img_A = Input(shape=self.img_shape)
        img_B = Input(shape=self.img_shape)

        # By conditioning on B generate a fake version of A
        fake_B = self.generator(img_A)

        # For the combined model we will only train the generator
        self.discriminator.trainable = False

        # Discriminators determines validity of translated images / condition pairs
        valid = self.discriminator([fake_B, img_B])

        self.combined = Model(inputs=[img_A, img_B], outputs=[valid, fake_B])
        self.combined.compile(loss=['mse', 'mae'],
                              loss_weights=[1, 100],
                              optimizer=optimizer)

    def build_generator(self):
        """U-Net Generator"""

        def conv2d(layer_input, filters, f_size=4, bn=True):
            """Layers used during downsampling"""
            d = Conv2D(filters, kernel_size=f_size,
                       strides=2, padding='same')(layer_input)
            d = LeakyReLU(alpha=0.2)(d)
            if bn:
                d = BatchNormalization(momentum=0.8)(d)
            return d

        def deconv2d(layer_input, skip_input, filters, f_size=4, dropout_rate=0):
            """Layers used during upsampling"""
            u = UpSampling2D(size=2)(layer_input)
            u = Conv2D(filters, kernel_size=f_size, strides=1,
                       padding='same', activation='relu')(u)
            if dropout_rate:
                u = Dropout(dropout_rate)(u)
            u = BatchNormalization(momentum=0.8)(u)
            u = Concatenate()([u, skip_input])
            return u

        # Image input
        d0 = Input(shape=self.img_shape)

        # Downsampling
        d1 = conv2d(d0, self.gf, bn=False)
        d2 = conv2d(d1, self.gf*2)
        d3 = conv2d(d2, self.gf*4)
        d4 = conv2d(d3, self.gf*8)
        d5 = conv2d(d4, self.gf*8)

        # Upsampling
        u1 = deconv2d(d5, d4, self.gf*8)
        u2 = deconv2d(u1, d3, self.gf*4)
        u3 = deconv2d(u2, d2, self.gf*2)
        u4 = deconv2d(u3, d1, self.gf)

        u5 = UpSampling2D(size=2)(u4)
        output_img = Conv2D(self.channels, kernel_size=4,
                            strides=1, padding='same', activation='tanh')(u5)

        return Model(d0, output_img)

    def build_discriminator(self):

        def d_layer(layer_input, filters, f_size=4, bn=True):
            """Discriminator layer"""
            d = Conv2D(filters, kernel_size=f_size,
                       strides=2, padding='same')(layer_input)
            d = LeakyReLU(alpha=0.2)(d)
            if bn:
                d = BatchNormalization(momentum=0.8)(d)
            return d

        img_A = Input(shape=self.img_shape)
        img_B = Input(shape=self.img_shape)

        # Concatenate image and conditioning image by channels to produce input
        combined_imgs = Concatenate(axis=-1)([img_A, img_B])

        d1 = d_layer(combined_imgs, self.df, bn=False)
        d2 = d_layer(d1, self.df*2)
        d3 = d_layer(d2, self.df*4)
        d4 = d_layer(d3, self.df*8)

        validity = Conv2D(1, kernel_size=2, strides=1, padding='same')(d4)

        return Model([img_A, img_B], validity)

    def train(self, epochs, batch_size=1, sample_interval=50, model_interval=500):

        start_time = datetime.datetime.now()

        # Load the dataset
        Y_train = np.load('C:\\AI\\x_train.npy')
        X_train = np.load('C:\\AI\\y_train.npy')

        # Rescale -1 to 1
        X_train = X_train / 127.5 - 1.
        X_train = np.expand_dims(X_train, axis=3)
        Y_train = Y_train / 127.5 - 1.
        Y_train = np.expand_dims(Y_train, axis=3)

        # Adversarial loss ground truths
        valid = np.ones((batch_size,) + self.disc_patch)
        fake = np.zeros((batch_size,) + self.disc_patch)

        n_batch = int(X_train.shape[0]/batch_size)

        for epoch in range(epochs):
            for batch_i in range(n_batch):
                # ---------------------
                #  Train Discriminator
                # ---------------------

                idx = np.random.randint(0, X_train.shape[0], batch_size)
                imgs_A = X_train[idx]
                imgs_B = Y_train[idx]

                # Condition on B and generate a translated version
                fake_B = self.generator.predict(imgs_A)

                # Train the discriminators (original images = real / generated = Fake)
                d_loss_real = self.discriminator.train_on_batch(
                    [imgs_A, imgs_B], valid)
                d_loss_fake = self.discriminator.train_on_batch(
                    [fake_B, imgs_B], fake)
                d_loss = 0.5 * np.add(d_loss_real, d_loss_fake)

                # -----------------
                #  Train Generator
                # -----------------

                # Train the generators
                g_loss = self.combined.train_on_batch(
                    [imgs_A, imgs_B], [valid, imgs_B])

                elapsed_time = datetime.datetime.now() - start_time
                # Plot the progress
                print("[Epoch %d/%d] [Batch %d/%d] [D loss: %f, acc: %3d%%] [G loss: %f] time: %s" % (epoch, epochs,
                                                                                                      batch_i, n_batch,
                                                                                                      d_loss[0], 100 *
                                                                                                      d_loss[1],
                                                                                                      g_loss[0],
                                                                                                      elapsed_time))

                # If at save interval => save generated image samples
                if batch_i % sample_interval == 0:
                    self.sample_images(epoch, batch_i)
                if batch_i % model_interval == 0:
                    self.generator.save_weights(
                        "models/pix2pix_inv_generator.h5")
                    self.discriminator.save_weights(
                        "models/pix2pix_inv_discriminator.h5")

    def sample_images(self, epoch, batch_i):
        os.makedirs('images/%s' % self.dataset_name, exist_ok=True)
        r, c = 3, 3

        # Load the dataset
        Y_test = np.load('C:\\AI\\x_test.npy')
        X_test = np.load('C:\\AI\\y_test.npy')

        # Rescale -1 to 1
        X_test = X_test / 127.5 - 1.
        X_test = np.expand_dims(X_test, axis=3)
        Y_test = Y_test / 127.5 - 1.
        Y_test = np.expand_dims(Y_test, axis=3)

        idx = np.random.randint(0, X_test.shape[0], 3)
        imgs_A = X_test[idx]
        imgs_B = Y_test[idx]

        fake_B = self.generator.predict(imgs_A)

        gen_imgs = np.concatenate([imgs_A, fake_B, imgs_B])

        # Rescale images 0 - 1
        gen_imgs = 0.5 * gen_imgs + 0.5

        titles = ['Original', 'Generated', 'Condition']
        fig, axs = plt.subplots(r, c)
        cnt = 0
        for i in range(r):
            for j in range(c):
                axs[i, j].imshow(gen_imgs[cnt, :, :, 0], cmap='gray')
                axs[i, j].set_title(titles[i])
                axs[i, j].axis('off')
                cnt += 1
        fig.savefig("images/%s/%d_%d.png" %
                    (self.dataset_name, epoch, batch_i))
        plt.close()

    def get_end_title(self):
        self.generator.load_weights('models/pix2pix_inv_generator.h5')
        
        r, c = 1, 4

        # Load the dataset
        X_test = np.load('C:\\AI\\baogaojieshu_test.npy')

        # Rescale -1 to 1
        X_test = X_test / 127.5 - 1.
        X_test = np.expand_dims(X_test, axis=3)

        idx = np.array([0, 1, 2, 3])
        imgs_A = X_test[idx]
        fake_B = self.generator.predict(imgs_A)
        gen_imgs = fake_B

        # Rescale images 0 - 1
        gen_imgs = 0.5 * gen_imgs + 0.5

        fig, axs = plt.subplots(r, c)
        cnt = 0
        for i in range(c):
            axs[i].imshow(gen_imgs[cnt, :, :, 0], cmap='gray')
            axs[i].axis('off')
            cnt += 1
        fig.savefig("images/baogaojieshu.png")
        plt.close()

if __name__ == '__main__':
    gan = Pix2Pix()
    # gan.train(epochs=5, batch_size=1, sample_interval=200, model_interval=500)
    gan.get_end_title()
