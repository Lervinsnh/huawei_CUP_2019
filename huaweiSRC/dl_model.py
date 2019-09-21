# -*- coding: utf-8 -*-
"""
Created on Fri Sep 20 09:26:34 2019
@author: lervisnh
"""
import os
import tensorflow as tf
from tensorflow import layers
import numpy as np
from read_data import batch_data_generator

import time


class our_model:
    def __init__(self, input_dim, #输入维度
                 hidden_layers_info, #隐藏层，以字典格式保存信息
                                #层数：层类型、激活函数、神经元（filters）个数，其他（CNN）：kernel_size、strides
                 output_dim = 1, #输出维度
                 epoches = 200,  #训练最大总步数
                 minibatch_size = 10240, #mini batch训练大小
                 ):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.hidden_layers_info = hidden_layers_info
        self.epoches = epoches
        self.minibatch_size = minibatch_size
        try: 
            self.codes_path = os.getcwd() #代码存放地址
            father_path = os.path.abspath(os.path.join(os.getcwd(), "..")) #上一级目录
            train_set_path = father_path+'/train_set'
            test_set_path = father_path+'/test_set'
            if os.path.exists(train_set_path) and os.path.exists(train_set_path): #train数据集存放地址
                self.train_set_path = train_set_path
                self.test_set_path = test_set_path
                print('Train_set and Test_set (validation_set) directory exists!')
        except:
            print('Train_set or Test_set (validation_set) directory doesn\'t exist, please CHECK!')
            
    
    def building(self, input_layer):
        model_layers = [input_layer]
        for hidden_layer in self.hidden_layers_info: #关键字，层数1 2 3 4 5...
            this_layer_info = self.hidden_layers_info[hidden_layer]
            prev_layer = model_layers[-1]
            #普通层
            if this_layer_info['layer_type'] == 'Dense':
                this_layer = layers.Dense( units = this_layer_info['units_filters'],
                                           activation = this_layer_info['activation'],
                                           name = 'hidden_'+str(hidden_layer)+this_layer_info['layer_type']
                                           )(prev_layer)
                model_layers.append( this_layer )
            #一维卷积层
            elif this_layer_info['layer_type'] == 'Conv1D':
                this_layer = layers.Conv1D( filters = this_layer_info['units_filters'],
                                            activation = this_layer_info['activation'],
                                            kernel_size = this_layer_info['kernel_size'],
                                            strides = this_layer_info['strides'],
                                            padding = 'same',
                                            name = 'hidden_'+str(hidden_layer)+this_layer_info['layer_type']
                                            )(prev_layer)
                model_layers.append( this_layer )
        output = layers.Dense(units = self.output_dim, name = 'output_layer')( model_layers[-1] )
        return output
    
    
    def training(self):
        new_graph = tf.Graph()
        with new_graph.as_default() as new_g:
            #input占位符  模型输出
            input_layer = tf.placeholder(tf.float32, [None, self.input_dim], name = 'input_layer')
            output_layer = self.building(input_layer)
            #输出label占位符
            regression  = tf.placeholder(tf.float32, [None, ], name = 'target_labels')
            #目标函数
            rmse = tf.sqrt(tf.reduce_mean(tf.squared_difference(output_layer, regression)))
            # learning rate
            learning_rate = tf.train.exponential_decay(1.5e-3, self.epoches,
                                         decay_steps=self.epoches//10,
                                         decay_rate=0.9,staircase=True)
            solver = tf.train.AdamOptimizer(learning_rate).minimize(rmse)
            
        with tf.Session(graph = new_g) as sess:
            # tf.initialize_all_variables() no long valid from
            # 2017-03-02 if using tensorflow >= 0.12
            if int((tf.__version__).split('.')[1]) < 12 and int((tf.__version__).split('.')[0]) < 1:
                init = tf.initialize_all_variables()
            else:
                init = tf.global_variables_initializer()
            sess.run(init)
            
            # 首先计算总批数，保证每次循环训练集中的每个样本都参与训练，不同于批量训练
            epoches_val_rmse = [] #保存分批计算文件的验证RMSE
            epoches_mean_val_rmse = [] #保存分批计算文件的验证RMSE均值
            epoches_var_val_rmse = [] #保存分批计算文件的验证RMSE方差
            for epoch in range(self.epoches):
                epoch_time_start=time.time()
                # 迭代所有文件
                a_batch_data_generator = batch_data_generator(self.train_set_path, files_split_rate=.01)
                val_rmse = []
                for load_files, (inputs, labels) in enumerate(a_batch_data_generator.batch_generator()):
                    '''
                    #检查inputs
                    try:
                        if np.nan not in inputs:
                            pass
                        if np.inf not in inputs:
                            pass
                    except:
                        print( 'np.nan or np.inf in inputs !' )
                    #检查labels
                    try:
                        if np.nan not in labels:
                            pass
                        if np.inf not in labels:
                            pass
                    except:
                        print( 'np.nan or np.inf in labels !' )
                    '''
                    #乱序化输入输出对
                    _ = np.random.get_state()
                    np.random.shuffle(inputs)
                    np.random.set_state(_)
                    np.random.shuffle(labels)
                    #本次迭代读取文件验证集
                    val_samples_n = int(inputs.shape[0]*0.05)+1#取5%为验证集，辅助实现early stopping
                    val_inputs, val_labels = inputs[0:val_samples_n+1,:], labels[0:val_samples_n+1]
                    #本次迭代读取文件训练集
                    inputs, labels = inputs[val_samples_n+1:,:], labels[val_samples_n+1:]
                    # mini batch
                    total_batch = int( inputs.shape[0] / self.minibatch_size ) #总批数
                    for i in range( total_batch+1 ): #range(total_batch+1) 或 range(total_batch)
                        batch_xs = inputs[ i*self.minibatch_size : (i+1)*self.minibatch_size , : ]
                        batch_ys = labels[ i*self.minibatch_size : (i+1)*self.minibatch_size]
                        _, c = sess.run((solver, rmse), 
                                        feed_dict={input_layer:batch_xs, regression:batch_ys})
                        #print('Mini Batch: ', i, ' / ', total_batch )
                    val_rmse.append( sess.run(rmse, feed_dict={input_layer:val_inputs, regression:val_labels}) )
                    #print('Load files.  No. ', load_files+1)
                    # 一次文件迭代完毕
                    
                epoches_val_rmse.append(val_rmse)
                epoches_mean_val_rmse.append(np.mean(val_rmse))
                epoches_var_val_rmse.append(np.var(val_rmse))
                # 所有训练集跑完一个epoch
                epoch_time_end=time.time()
                #一个epoch运行时间
                running_time_a_epoch = (epoch_time_end-epoch_time_start)/60
                print("""Epoch:%d     #     Running time/epoch (min):%.3f""" 
                      %( epoch+1, running_time_a_epoch))
                print("""Validation RMSE mean:%.3f #  Validation RMSE var:%.3f""" 
                      %( epoches_mean_val_rmse[-1], epoches_var_val_rmse[-1]))
                
                #每 多少 个 epoch保存一下
                check_save_point = 5
                if not (epoch+1)%check_save_point:
                    path_to_save = self.codes_path+'/saving_model/variables'
                    self.saving(sess, path_to_save)
                
                #最近训练的 patience 次，误差在 min_delta 内
                min_delta = 0.05
                patience = 10
                if epoch > patience and \
                   abs( np.mean(epoches_mean_val_rmse[-1-patience:-1])
                        -epoches_mean_val_rmse[-1] ) < min_delta:
                    #保存最优模型模型
                    path_to_save = self.codes_path+'/saving_model/variables'
                    self.saving(sess, path_to_save)
                    print('########################')
                    print('!!!  Early stopping  !!!')
                    print('Min delta:', min_delta)
                    print('Patience:', patience)
                    print('-----------------------------------')
                    print('Path to save model: ', path_to_save)
                    print('-----------------------------------')
                    break #早停
            self.session =  sess
        
    def saving(self, sess, path_to_save):
        saver = tf.train.Saver()
        saver.save(sess, path_to_save)
        
    def predicting(self):
        #合并test的数据集
        a_batch_data_generator = batch_data_generator(self.test_set_path)
        test_inputs = a_batch_data_generator.merging()
        #input占位符  模型输出
        inputs = tf.placeholder(tf.float32, [None, self.input_dim], name = 'input_layer')
        predictions = self.building(inputs)
        if 'session' in self.__dir__():
            with self.session as sess:
                prediction = sess.run(predictions, feed_dict={inputs:test_inputs})
        else:
            with tf.Session() as sess:
                path_to_save = self.codes_path+'/saving_model/variables.meta'
                restoration = tf.train.import_meta_graph(path_to_save)
                restoration.restore(sess, os.path.join(self.codes_path+'/saving_model', 
                                                       'variables'))
                prediction = sess.run(predictions, feed_dict={inputs:test_inputs})
        return prediction
    
if  __name__=='__main__':
    hidden_layers_info = {1:{'layer_type':'Dense', 'activation':'tanh', 'units_filters':10 },
                          2:{'layer_type':'Dense', 'activation':'relu', 'units_filters':10, \
                                                                                 'kernel_size':4, \
                                                                                 'strides':2},
                          3:{'layer_type':'Dense', 'activation':'relu', 'units_filters':8 },
                          4:{'layer_type':'Dense', 'activation':'tanh', 'units_filters':6 },
                          }
    our_one_model = our_model(input_dim=6, 
                              hidden_layers_info=hidden_layers_info, 
                              epoches = 200,
                              minibatch_size=2048 )
    our_one_model.predicting()
    #our_one_model.training()
    