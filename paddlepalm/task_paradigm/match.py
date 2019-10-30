# -*- coding: UTF-8 -*-
#   Copyright (c) 2019 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import paddle.fluid as fluid
from paddlepalm.interface import task_paradigm
from paddle.fluid import layers

class TaskParadigm(task_paradigm):
    '''
    matching
    '''
    def __init__(self, config, phase, backbone_config=None):
        self._is_training = phase == 'train'
        self._hidden_size = backbone_config['hidden_size']

        if 'initializer_range' in config:
            self._param_initializer = config['initializer_range']
        else:
            self._param_initializer = fluid.initializer.TruncatedNormal(
                scale=backbone_config.get('initializer_range', 0.02))
        if 'dropout_prob' in config:
            self._dropout_prob = config['dropout_prob']
        else:
            self._dropout_prob = backbone_config.get('hidden_dropout_prob', 0.0)

    
    @property
    def inputs_attrs(self):
        if self._is_training:
            reader = {"label_ids": [[-1, 1], 'int64']}
        else:
            reader = {}
        bb = {"sentence_pair_embedding": [[-1, self._hidden_size], 'float32']}
        return {'reader': reader, 'backbone': bb}

    @property
    def outputs_attrs(self):
        if self._is_training:
            return {"loss": [[1], 'float32']}
        else:
            return {"logits": [[-1, 1], 'float32']}

    def build(self, inputs):
        if self._is_training:
            labels = inputs["reader"]["label_ids"] 
        cls_feats = inputs["backbone"]["sentence_pair_embedding"]

        if self._is_training:
            cls_feats = fluid.layers.dropout(
                x=cls_feats,
                dropout_prob=self._dropout_prob,
                dropout_implementation="upscale_in_train")

        logits = fluid.layers.fc(
            input=cls_feats,
            size=2,
            param_attr=fluid.ParamAttr(
                name="cls_out_w",
                initializer=self._param_initializer),
            bias_attr=fluid.ParamAttr(
                name="cls_out_b",
                initializer=fluid.initializer.Constant(0.)))

        if self._is_training:
            ce_loss, probs = fluid.layers.softmax_with_cross_entropy(
                logits=logits, label=labels, return_softmax=True)
            loss = fluid.layers.mean(x=ce_loss)
            return {'loss': loss}
        else:
            return {'logits': logits}

