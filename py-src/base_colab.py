# -*- coding: utf-8 -*-
"""Model Training - Mamba.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1XEP9EkBDa17iivz--GOj9CfZRHwz1VUQ

# 🔗 Dependencies

Downloads and installs dependencies for the entire notebook
"""

!pip install transformers mamba_ssm causal_conv1d datasets wandb

"""# 🪛 Trainer and Helpers Implementation

Implementation of the main classes used throughout the notebook
"""

import torch
import numpy as np


class CallableMeta(type):
    def __call__(cls, *args, **kwargs):
        return cls.__call__(*args, **kwargs)


class GlobalsMeta(type):
    def __getattr__(cls, key):
        if key in globals():
            return globals()[key]
        else:
            print(f"Variable '{key}' is undefined in {cls.__name__}, returning None")
            return None

    def __setattr__(cls, key, value):
        globals()[key] = value

class Globals(metaclass=GlobalsMeta):
    pass


class Util:
    @staticmethod
    def GetDevice():
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")


    @staticmethod
    def RoundNumber(number):
        suffixes = ['', 'k', 'm', 'b']

        if number < 1000:
            return str(number)

        magnitude = 0
        while abs(number) >= 1000:
            magnitude += 1
            number /= 1000.0

        return '{:.0f}{}'.format(number, suffixes[magnitude])


    @staticmethod
    def RandomCode():
        import math
        import random

        code = '';
        chars = '0123456789abcdef'
        count = 8;

        for i in range(0, count):
          code += chars[math.floor(random.randrange(len(chars)))]

        return code


    @staticmethod
    def GetNumParams(model):
        size = sum(p.numel() for p in model.parameters())
        rounded_size = Util.RoundNumber(size)

        return size, rounded_size


    @staticmethod
    def Tee(file, str):
        print(str)

        with open(file, 'a') as f:
            f.write(f"{str}\n")


class Colab:
    @staticmethod
    def ClearOutput():
        from IPython.display import clear_output
        clear_output()


    @staticmethod
    def Terminate():
        from google.colab import runtime
        runtime.unassign()

class ByteTokenizer():
    def __init__(self):
        self.vocab_size = 256
        self.Log()


    def __call__(self, seed_text):
        return self.encode(seed_text)


    def encode(self, seed_text, return_tensors=None):
        import numpy as np
        input_ids = np.frombuffer(seed_text.encode('ascii', errors='ignore'), dtype=np.uint8)

        if (return_tensors == "pt"):
            input_ids = torch.from_numpy(np.copy(input_ids)[None, :]).type(torch.long)

        return input_ids


    def decode(self, input_ids):
        flattened_tensor = input_ids.view(-1)
        integer_tensor = flattened_tensor.type(torch.uint8) # cast to uint8 (unsigned char) for decode
        text = bytearray(integer_tensor.tolist()).decode('ascii', errors='ignore')
        return text


    def Log(self):
        Util.Tee("config_log.txt", f"Vocabulary contains {self.vocab_size} unique tokens")

from datasets import load_dataset

class GenerateData(metaclass=CallableMeta):
    @staticmethod
    def __call__(dataset, tokenizer, seq_length, batch_size):
        dataset     = dataset
        tokenizer   = tokenizer
        seq_length  = seq_length
        batch_size  = batch_size
        vocab_size  = len(tokenizer.vocab)

        texts = dataset["train"]["text"]
        text  = GenerateData.ConcatSplits(texts)


        input_ids = tokenizer.encode(text)
        input_ids = GenerateData.ClipOutOfVocab(input_ids, vocab_size)

        batches, num_batches =  GenerateData.BatchSequences(input_ids, seq_length, batch_size)
        GenerateData.Log(seq_length, num_batches, batch_size, batches)

        return batches, num_batches


    @staticmethod
    def Log(seq_length, num_batches, batch_size, batches):
        Util.Tee("config_log.txt", f"Dataset contains {num_batches} batches of {batch_size} sequences of {seq_length} tokens each ({Util.RoundNumber(seq_length * batch_size * num_batches)} tokens total)")
        Util.Tee("config_log.txt", f"Model's context window is {seq_length * batch_size} (seq_length * batch_size)")
        Util.Tee("config_log.txt", f"Batches shape is {torch.stack(batches).shape}")


    @staticmethod
    def ConcatSplits(texts):
        splits = [elem for sublist in texts for elem in sublist]
        text = ''.join(splits)
        return text


    @staticmethod
    def ClipOutOfVocab(input_ids, vocab_size):
        clipped = [min(token, vocab_size) for token in input_ids]
        return clipped


    @staticmethod
    def BatchSequences(input_ids, seq_length, batch_size):
        if not isinstance(input_ids, np.ndarray):
            input_ids = np.array(input_ids)

        num_batches = len(input_ids) // (seq_length * batch_size)
        total_elements = num_batches * seq_length * batch_size

        trimmed_array = input_ids[:total_elements]
        array_reshaped = trimmed_array.reshape((num_batches, batch_size, seq_length))

        tensor_batches = []
        for batch in array_reshaped:
            tensor_batch = torch.tensor(batch, dtype=torch.long).to(Util.GetDevice())
            tensor_batches.append(tensor_batch)

        return tensor_batches, num_batches

import time

class Time(metaclass=CallableMeta):
    time_init = None
    time_last = None


    @staticmethod
    def __call__():
        return Time.Get()


    @staticmethod
    def Get():
        time_current = time.time()

        if Time.time_init == None:
            Time.time_init = time_current

        if Time.time_last == None:
            Time.time_last = time_current

        return time_current


    @staticmethod
    def FormatString(number):
        number = round(number)

        hours = number // 3600
        minutes = (number % 3600) // 60
        seconds = number % 60

        time_string = ""

        if hours > 0:
            time_string += str(hours) + "h "
        if minutes > 0 or hours > 0:
            time_string += str(minutes) + "m "
        time_string += str(seconds) + "s"

        return time_string


    @staticmethod
    def FormatSecond(time_string):
        number = 0
        parts = time_string.split()

        for part in parts:
            if part.endswith('h'):
                number += int(part[:-1]) * 3600
            elif part.endswith('m'):
                number += int(part[:-1]) * 60
            elif part.endswith('s'):
                number += int(part[:-1])

        return number


    @staticmethod
    def Up(raw=False):
        time_current = Time()
        time_up = time_current - Time.time_init

        return time_up if raw is True else Time.FormatString(time_up)


    @staticmethod
    def Step(raw=False):

        time_current = Time()
        time_step = time_current - Time.time_last
        Time.time_last = time_current

        return time_step if raw is True else Time.FormatString(time_step)

import os
import wandb


class Wandb(metaclass=CallableMeta):
    wandb_has_init = False

    @staticmethod
    def Init():
        if Globals.wandb_log_run is False:
            return

        if Wandb.wandb_has_init is True:
            return

        Wandb.wandb_has_init = True

        project  = Globals.wandb_project
        entity   = Globals.wandb_entity
        api_key  = Globals.wandb_api_key
        name     = Globals.wandb_name

        if name is None or name == "":
            name = "run-" + Util.RandomCode()

        os.environ["WANDB_API_KEY"] = api_key

        wandb.init(project=project, entity=entity, name=name)


    @staticmethod
    def Log(args):
        if Globals.wandb_log_run is False:
            return

        if Wandb.wandb_has_init is False:
            Wandb.Init()

        if Wandb.wandb_has_init is True:
            wandb.log(args)


    @staticmethod
    def Finish():
        if Globals.wandb_log_run is False:
            return

        if Wandb.wandb_has_init is True:
            wandb.finish()

class TrainModel(metaclass=CallableMeta):
    train_step = 0


    @staticmethod
    def __call__(model, batches, num_epochs, learning_rate):
        optimizer     = torch.optim.Adam(model.parameters(), lr=learning_rate)
        criterion     = torch.nn.CrossEntropyLoss()

        model.train()
        Wandb.Init()

        for epoch in range(num_epochs):
            for batch in range(num_batches):
                input_ids = batches[batch]

                loss = model.compute_loss(input_ids)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                TrainModel.LogStep(epoch, num_epochs, batch, num_batches, loss)

        Wandb.Finish()



    @staticmethod
    def ComputeTime(step, num_epochs, num_batches):
        time_step       = Time.Step(raw=True)
        time_up         = Time.Up(raw=True)
        time_per_epoch  = time_step * num_batches * num_epochs
        time_remain     = time_per_epoch - time_up if time_up < time_per_epoch else 0

        return Time.FormatString(time_up), Time.FormatString(time_per_epoch), Time.FormatString(time_remain)


    @staticmethod
    def LogStep(epoch, num_epochs, batch, num_baches, loss, log_every=10):
        step = TrainModel.train_step
        loss = loss.item()

        time_up, time_per_epoch, time_remain = TrainModel.ComputeTime(step, num_epochs, num_batches)

        wandb_args = {"step": step, "epoch": epoch, "batch": batch, "loss": loss}
        Wandb.Log(wandb_args)

        if step % log_every == 0:
            Util.Tee("training_log.txt", f"Step: {step}\t\tEpoch: {epoch} / {num_epochs}\t\tBatch: {batch} / {num_batches}\t\tLoss: {round(loss, 4)}\t\tTime: {time_up} / {time_per_epoch}\t({time_remain} remaining)")

        if Globals.infer_during_training is True and step % (log_every * 10) == 0:
            Util.Tee("inference_log.txt", f"{model.generate_text(Globals.tokenizer, Globals.seed_text, Globals.num_predict)}\n")

        TrainModel.train_step += 1

from types import MethodType

class GenerateModel(metaclass=CallableMeta):
    @staticmethod
    def __call__(params, model_class, config_class):
        config = config_class(**params)
        model = model_class(config).to(Util.GetDevice())

        model.compute_loss = MethodType(GenerateModel.AutoRegressiveLossFunction, model)
        model.generate_text = MethodType(GenerateModel.GenerateText, model)
        model.save = MethodType(GenerateModel.SaveToPytorch, model)

        GenerateModel.Log(model)

        return model, config

    @staticmethod
    def Log(model):
        model_size, rounded_model_size = Util.GetNumParams(model)
        Util.Tee("config_log.txt", f"Model has {model_size} ({rounded_model_size}) parameters")

    @staticmethod
    def AutoRegressiveLossFunction(self, input_ids, labels=None, criterion=None):
        model = self
        lm_logits = model(input_ids).logits

        labels = input_ids.to("cuda")
        shift_logits = lm_logits[:, :-1, :].contiguous()
        labels = labels[:, 1:].contiguous()

        loss_fct = criterion or torch.nn.CrossEntropyLoss()
        lm_loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), labels.view(-1))

        return lm_loss

    @staticmethod
    def GenerateText(self, tokenizer, seed_text, num_predict):
        model = self
        max_len = num_predict + len(seed_text)

        with torch.no_grad():
            encoded_ids = tokenizer.encode(seed_text)
            input_ids = torch.tensor(encoded_ids).unsqueeze(0).to(Util.GetDevice())
            output = model.generate(input_ids, max_length=max_len)

            logits = output[0].tolist()
            text = tokenizer.decode(logits)
        return text

    @staticmethod
    def SaveToPytorch(self):
        model = self
        model.save_pretrained('./')

"""# Tokenizer implementation"""

from collections import Counter

def most_occurring_pair(arr):
    # Create pairs of adjacent elements, ignoring pairs where the second element > 255
    pairs = [(a, b) for a, b in zip(arr[:-1], arr[1:]) if b <= 255]

    pair_counts = Counter(pairs)
    if not pair_counts:
        return None

    most_common_pair = max(pair_counts, key=pair_counts.get)
    return list(most_common_pair)



def replace_pair(initial_list, pair_to_remove, replace_with):
    result = []
    i = 0

    while i < len(initial_list):
        if i + 1 < len(initial_list) and initial_list[i:i+2] == pair_to_remove:
            result.append(replace_with)
            i += 2

        else:
            result.append(initial_list[i])
            i += 1

    return result




import struct

class Token:
    def __init__(self, byte, prev):
        self.byte = byte
        self.prev = prev

    def pack(self):
        return struct.pack("=B H", ord(self.byte), self.prev)

    def __str__(self):
        return f"{self.byte}, {self.prev}"

    def to_binary(self):
        return self.pack()

    @classmethod
    def from_binary(cls, data):
        if len(data) != 3:
            raise ValueError("Data has invalid length, Exprected 3 bytes.")

        byte, prev = struct.unpack("=B H", data)
        return cls(chr(byte), prev)


class Vocab:
    def __init__(self):
        self.clear()

    def __getitem__(self, id):
        return self.tokens[id]

    def __setitem__(self, id, token):
        self.tokens[id] = token

    def clear(self):
        self.tokens = []
        self.vocab_size = 0

    def __len__(self):
        return self._get_size()

    def _get_size(self):
        return self.vocab_size

    def __iadd__(self, token):
        self._add_token(token)
        return self

    def __add__(self, token):
        return self._add_token(token)

    def _add_token(self, token):
        self.tokens.append(token)
        self.vocab_size += 1
        return self.vocab_size - 1

    def find(self, byte, prev):
        for i in range(self.vocab_size):
            token = self.tokens[i]

            if byte == token.byte and prev == token.prev:
                return i

        return 0

    def __str__(self):
        text = '['
        n_tokens = len(self.tokens)

        for i in range(n_tokens):
            text += '{' + str(self.tokens[i]) + ('}, ' if i < n_tokens - 1 else '}]')

        return text


    def to_file(self, file):
        with open(file, 'ab') as f:
            for token in self.tokens:
                f.write(token.to_binary())

    def from_file(self, file):
        self.clear()

        with open(file, 'rb') as f:
            while True:
                try:
                    data = f.read(3)
                    token = Token.from_binary(data)
                    self += token

                except ValueError:
                    break


class Tokenizer:
    def __init__(self):
        self.vocab = Vocab()
        self._init_byte_level()

    def _init_byte_level(self):
        self.vocab.clear()

        for i in range(256):
            token = Token(chr(i), 0)
            self.vocab += token


    def train(self, text, target_length=None):
        arr = [ord(c) for c in text]

        while True:
            if target_length is not None:
                if len(self.vocab) >= target_length:
                    break

            pair = most_occurring_pair(arr)

            if arr is None or pair is None:
                break;

            byte = chr(pair[1])
            prev = pair[0]
            token = Token(byte, prev)
            id = self.vocab + token

            arr = replace_pair(arr, pair, id)


    def _decode_one(self, id):
        text = ""
        while True:
            token = self.vocab[id]

            text += token.byte
            if token.prev == 0:
                break

            id = token.prev

        return text[::-1]

    def decode(self, ids):
        if not isinstance(ids, list):
            ids = [ids]

        text = ""
        for id in ids:
            text += self._decode_one(id)

        return text

    def _encode_one(self, text):
        prev = 0

        for i in range(len(text)):
            next = self.vocab.find(text[i], prev)
            if next == 0:
                return prev, text[i:]

            prev = next

        return prev, ""

    def encode(self, text):
        if isinstance(text, list):
            texts = text
            text = ""

            for i in range(len(texts)):
                text += texts[i]

        ids = []

        while text != "":
            id, text = self._encode_one(text)

            if id == 0:
                text = text[1:]

            ids.append(id)

        return ids


    def add_one_special_token(self, text):
        prev = 0
        byte = None

        for i in range(len(text)):
            byte = text[i]
            token = self.vocab.find(byte, prev)

            if token:
                prev = token
                continue

            token = Token(byte, prev)
            prev = self.vocab + token

        return prev

    def add_special_token(self, texts):
        if not isinstance(texts, list):
            texts = [texts]

        for i in range(len(texts)):
            text = texts[i]
            self.add_one_special_token(text)

    def __str__(self):
        return str(self.vocab)

    def to_file(self, file):
        self.vocab.to_file(file)

    def from_file(self, file):
        self.vocab.from_file(file)

"""# ⚔️ Model Specific Code


This Google Colab notebook requires a GPU instance

For a free GPU instance, please use the NVIDIA T4 GPU, as part of the Free Google Colab Plan

"""

#@title # Training Parameters

#@markdown This code block uses either Mamba or GPT-2 as base architecture for language modeling

#@markdown The parameters defined here can be used with both models, with their code blocks written below

#@markdown -----



#@markdown ## 📃 Dataset and training parameters

dataset_path = "flpelerin/tinystories-1k"                #@param {type: "string"}

num_epochs = 2                                            #@param {type: "number"}
learning_rate = 1e-4                                      #@param {type: "number"}

#@markdown -----



#@markdown ## ✂️ Tokenizer

#@markdown Leave empty for Byte Tokenizer (character-level)

tokenizer_path = "./tokenizer.bin"                                       #@param {type: "string"}

#@markdown -----



#@markdown ## 📏 Context window

#@markdown Context window = seq_length * batch_size

seq_length = 1024                                         #@param {type: "number"}
batch_size = 4                                            #@param {type: "number"}

#@markdown -----



#@markdown ## 🔧 Model parameters

d_model = 2048                                             #@param {type: "number"}
n_layer = 36                                              #@param {type: "number"}

# Model sizes for Mamba, from the paper: https://arxiv.org/abs/2312.00752
# params  n_layers  d_model   vocab_size
# 125M    12        768       32000
# 250M    24        1024      32000
# 790M    24        1536      32000
# 1.3B    24        2048      32000

# Model sizes for Mamba, from the paper: https://d4mucfpksywv.cloudfront.net/better-language-models/language_models_are_unsupervised_multitask_learners.pdf
# params  n_layers  d_model   vocab_size
# 117M    12        768       32000
# 345M    24        1024      32000
# 762M    36        1280      32000
# 1542M   48        1600      32000

#@markdown -----



#@markdown ## ✨ Inference parameters

seed_text = "One day, "                                   #@param {type: "string"}
num_predict = 256                                         #@param {type: "number"}

infer_during_training = True                              #@param {type: "boolean"}

#@markdown -----



#@markdown ## 📌 Weights & Biases parmeters

wandb_project = "snakes-slimorca"                        #@param {type: "string"}
wandb_entity = "florianpelerin110304"                     #@param {type: "string"}

#@markdown Leave empty for random name
wandb_name = ""                                           #@param {type: "string"}

wandb_api_key="860f8753998c6e6dc356914de07e8855aa2f9642"  #@param {type: "string"}
wandb_log_run = True                                      #@param {type: "boolean"}

#@markdown -----

#@title # Mamba Training Code



tokenizer = Tokenizer()
if tokenizer_path != "":
    tokenizer.from_file(tokenizer_path)

vocab_size = len(tokenizer.vocab)
Util.Tee("config_log.txt", f"Tokenizer has {vocab_size} unique tokens")



dataset = load_dataset(dataset_path)
batches, num_batches = GenerateData(dataset, tokenizer, seq_length, batch_size)




from mamba_ssm.models.mixer_seq_simple import MambaLMHeadModel
from mamba_ssm.models.config_mamba import MambaConfig

# Mamba specific code
params = {
    "vocab_size": vocab_size,

    "d_model": d_model,
    "n_layer": n_layer,

    "tie_embeddings": False,         # NO SHARED CLASSIFIER
}

model_class = MambaLMHeadModel
config_class = MambaConfig
model, config = GenerateModel(params, model_class, config_class)



#TrainModel(model, batches, num_epochs, learning_rate)

model.save()

#Colab.Terminate()

"""#Model export to C format"""

#@title Export to C format

import os
import struct
import argparse
import json
import numpy as np
import torch




def load_model(model_path):
    model = torch.load(model_path, map_location='cpu')

     # remove the 'backbone.' prefix from the keys
    unwanted_prefix = 'backbone.'
    for k,v in list(model.items()):
        if k.startswith(unwanted_prefix):
            model[k[len(unwanted_prefix):]] = model.pop(k)

    return model


def load_config(config_path):
    with open(config_path) as f:
        config = json.load(f)

    return config


def serialize_fp32(file, tensor):
    """ writes one fp32 tensor to file that is open in wb mode """
    d = tensor.detach().cpu().view(-1).to(torch.float32).numpy()
    b = struct.pack(f'{len(d)}f', *d)
    file.write(b)


def write_weights(file, model, key):
    """ writes the layer weights to file """
    print(f"writing {key} {list(model[key].shape)[::-1]}")
    serialize_fp32(file, model[key])


def write_layer_weights(file, model, layer, n_layers):
    """ writes the layer weights to file """
    print(f"writing {layer % n_layers} {list(model[layer % 0].shape)[::-1]}")
    for n in range(n_layers):
        serialize_fp32(file, model[layer % n])


def export_model(model, config, output_path):
    out_file = open(output_path, 'wb')

    n_layers = config['n_layer']

    '''
    Example of the model structure:
    embedding.weight - [50280, 768]
    layers.0.mixer.D - [1536]
    layers.0.mixer.in_proj.weight - [3072, 768]
    layers.0.mixer.conv1d.weight - [1536, 1, 4]
    layers.0.mixer.conv1d.bias - [1536]
    layers.0.mixer.x_proj.weight - [80, 1536]
    layers.0.mixer.dt_proj.weight - [1536, 48]
    layers.0.mixer.dt_proj.bias - [1536]
    layers.0.mixer.A_log - [1536, 16]
    layers.0.mixer.out_proj.weight - [768, 1536]
    layers.0.norm.weight - [768]
    norm_f.weight - [768]
    lm_head.weight - [50280, 768]
    '''

    for n in range(n_layers):
        model[f'layers.{n}.mixer.A'] = -torch.exp(model.pop(f'layers.{n}.mixer.A_log'))

    write_weights(out_file, model, 'embedding.weight')

    write_layer_weights(out_file, model, 'layers.%d.mixer.in_proj.weight', n_layers)
    write_layer_weights(out_file, model, 'layers.%d.mixer.conv1d.weight', n_layers)
    write_layer_weights(out_file, model, 'layers.%d.mixer.conv1d.bias', n_layers)
    write_layer_weights(out_file, model, 'layers.%d.mixer.x_proj.weight', n_layers)
    write_layer_weights(out_file, model, 'layers.%d.mixer.dt_proj.weight', n_layers)
    write_layer_weights(out_file, model, 'layers.%d.mixer.dt_proj.bias', n_layers)
    write_layer_weights(out_file, model, 'layers.%d.mixer.A', n_layers)
    write_layer_weights(out_file, model, 'layers.%d.mixer.D', n_layers)
    write_layer_weights(out_file, model, 'layers.%d.mixer.out_proj.weight', n_layers)
    write_layer_weights(out_file, model, 'layers.%d.norm.weight', n_layers)

    write_weights(out_file, model, 'norm_f.weight')
    write_weights(out_file, model, 'lm_head.weight')

    out_file.close()
    print(f"Exported model to {output_path}")



def export_config(model, config, output_path):
    """
    Exports the config to a C header file, following this configuration example:

        #define VOCAB_SIZE 256
        #define N_LAYER 12
        #define D_MODEL 768
        #define D_INNER 1536
        #define DT_RANK 48
        #define D_STATE 16
        #define D_CONV 4

    #define [KEY] [VALUE]
    key is converted to uppercase and value is the value from the config dictionary
    """

    vocab_size = config['vocab_size']
    rounded_vocab_size = vocab_size if vocab_size % 8 == 0 else vocab_size + (8 - (vocab_size % 8))

    with open(output_path, 'w') as f:
        f.write("#pragma once\n\n")
        f.write("#define VOCAB_SIZE %d\n" % vocab_size)
        f.write("#define ROUNDED_VOCAB_SIZE %d\n\n" % rounded_vocab_size)
        f.write("#define N_LAYER %d\n" % config['n_layer'])
        f.write("#define D_MODEL %d\n" % config['d_model'])
        f.write("#define D_INNER %d\n" % (2 * config['d_model']))
        f.write("#define DT_RANK %d\n" % model['layers.0.mixer.dt_proj.weight'].shape[1])
        f.write("#define D_STATE %d\n" % model['layers.0.mixer.A'].shape[1])
        f.write("#define D_CONV %d\n" % model['layers.0.mixer.conv1d.weight'].shape[2])

    print(f"Exported config to {output_path}")

"""
    values = [
        config['vocab_size'],                             # vocab_size
        config['n_layer'],                                # n_layer
        config['d_model'],                                # d_model
        2 * config['d_model'],                            # d_inner
        model['layers.0.mixer.dt_proj.weight'].shape[1],  # dt_rank
        model['layers.0.mixer.A'].shape[1],               # d_state
        model['layers.0.mixer.conv1d.weight'].shape[2]    # d_conv
    ]

    with open(output_path, 'wb') as f:
        for value in values:
            f.write(struct.pack('Q', value))

    print(f"Exported config to {output_path}")
"""






model = load_model("pytorch_model.bin")
config = load_config("config.json")



# Assuming model is a dictionary
for key in model.keys():
    print(key)




export_model(model, config, "model.bin")
export_config(model, config, "config.h")

#@title Quantized export to C format


# Model exporter to C binary format
import os
import struct
import argparse
import json

import numpy as np
import torch

def serialize_fp32(file, tensor):
    """ writes one fp32 tensor to file that is open in wb mode """
    d = tensor.detach().cpu().view(-1).to(torch.float32).numpy()
    b = struct.pack(f'{len(d)}f', *d)
    file.write(b)


def serialize_int8(file, tensor):
    """ writes one int8 tensor to file that is open in wb mode """
    d = tensor.detach().cpu().view(-1).numpy().astype(np.int8)
    b = struct.pack(f'{len(d)}b', *d)
    file.write(b)

def quantize_q80(w, group_size):
    """
    takes a tensor and returns the Q8_0 quantized version
    i.e. symmetric quantization into int8, range [-127,127]
    """
    assert w.numel() % group_size == 0
    ori_shape = w.shape
    w = w.float() # convert to float32
    w = w.reshape(-1, group_size)
    # find the max in each group
    wmax = torch.abs(w).max(dim=1).values
    # calculate the scaling factor such that float = quant * scale
    scale = wmax / 127.0
    # scale into range [-127, 127]
    quant = w / scale[:,None]
    # round to nearest integer
    int8val = torch.round(quant).to(torch.int8)
    # dequantize by rescaling
    fp32val = (int8val.float() * scale[:,None]).view(-1)
    fp32valr = fp32val.reshape(-1, group_size)
    # calculate the max error in each group
    err = torch.abs(fp32valr - w).max(dim=1).values
    # find the max error across all groups
    maxerr = err.max().item()
    return int8val, scale, maxerr


def write_weights(file, model, key):
    """ writes the layer weights to file """
    print(f"writing {key} {list(model[key].shape)[::-1]}")
    serialize_fp32(file, model[key])

def write_weights_q8_0(file, model, key, group_size=64):
    """ writes the quantized layer weights to file """
    q, s, err = quantize_q80(model[key], group_size)

    serialize_int8(file, q)
    serialize_fp32(file, s)

    print(f"{key} quantized {tuple(model[key].shape)} to Q8_0 with max error {err}")


def write_layer_weights(file, model, layer, n_layers):
    """ writes the layer weights to file """
    for n in range(n_layers):
        write_weights(file, model, layer % n)


def write_layer_weights_q8_0(file, model, layer, n_layers, group_size=64):
    #""" writes the layer weights to file """
    #for n in range(n_layers):
    #    write_weights_q8_0(file, model, layer % n, group_size)

    qtensors = { "q": [], "s": [] }

    for n in range(n_layers):
        q, s, err = quantize_q80(model[layer % n], group_size)

        qtensors["q"].append(q)
        qtensors["s"].append(s)

        print(f"{layer % n} quantized {tuple(model[layer % n].shape)} to Q8_0 with max error {err}")


    for q in qtensors["q"]:
        serialize_int8(file, q)

    for s in qtensors["s"]:
        serialize_fp32(file, s)



def load_config(config_path):
    with open(config_path) as f:
        config = json.load(f)

    return config

def load_model(model_path):
    model = torch.load(model_path, map_location='cpu')

     # remove the 'backbone.' prefix from the keys
    unwanted_prefix = 'backbone.'
    for k,v in list(model.items()):
        if k.startswith(unwanted_prefix):
            model[k[len(unwanted_prefix):]] = model.pop(k)

    return model


def export_model(model, config, output_path, group_size=64):
    out_file = open(output_path, 'wb')

    n_layers = config['n_layer']

    '''
    Example of the model structure:
    embedding.weight - [50280, 768]
    layers.0.mixer.D - [1536]
    layers.0.mixer.in_proj.weight - [3072, 768]
    layers.0.mixer.conv1d.weight - [1536, 1, 4]
    layers.0.mixer.conv1d.bias - [1536]
    layers.0.mixer.x_proj.weight - [80, 1536]
    layers.0.mixer.dt_proj.weight - [1536, 48]
    layers.0.mixer.dt_proj.bias - [1536]
    layers.0.mixer.A_log - [1536, 16]
    layers.0.mixer.out_proj.weight - [768, 1536]
    layers.0.norm.weight - [768]
    norm_f.weight - [768]
    lm_head.weight - [50280, 768]
    '''

    for n in range(n_layers):
        model[f'layers.{n}.mixer.A'] = -torch.exp(model.pop(f'layers.{n}.mixer.A_log'))

    #write_weights(out_file, model, 'embedding.weight')
    write_weights_q8_0(out_file, model, 'embedding.weight')


    #write_layer_weights(out_file, model, 'layers.%d.mixer.in_proj.weight', n_layers)
    write_layer_weights_q8_0(out_file, model, 'layers.%d.mixer.in_proj.weight', n_layers)


    write_layer_weights(out_file, model, 'layers.%d.mixer.conv1d.weight', n_layers)
    #write_layer_weights_q8_0(out_file, model, 'layers.%d.mixer.conv1d.weight', n_layers)

    write_layer_weights(out_file, model, 'layers.%d.mixer.conv1d.bias', n_layers)


    #write_layer_weights(out_file, model, 'layers.%d.mixer.x_proj.weight', n_layers)
    write_layer_weights_q8_0(out_file, model, 'layers.%d.mixer.x_proj.weight', n_layers)


    write_layer_weights(out_file, model, 'layers.%d.mixer.dt_proj.weight', n_layers)
    #write_layer_weights_q8_0(out_file, model, 'layers.%d.mixer.dt_proj.weight', n_layers)

    write_layer_weights(out_file, model, 'layers.%d.mixer.dt_proj.bias', n_layers)
    #write_layer_weights_q8_0(out_file, model, 'layers.%d.mixer.dt_proj.bias', n_layers)


    write_layer_weights(out_file, model, 'layers.%d.mixer.A', n_layers)
    write_layer_weights(out_file, model, 'layers.%d.mixer.D', n_layers)


    #write_layer_weights(out_file, model, 'layers.%d.mixer.out_proj.weight', n_layers)
    write_layer_weights_q8_0(out_file, model, 'layers.%d.mixer.out_proj.weight', n_layers)


    write_layer_weights(out_file, model, 'layers.%d.norm.weight', n_layers)
    write_weights(out_file, model, 'norm_f.weight')


    #write_weights(out_file, model, 'lm_head.weight')
    write_weights_q8_0(out_file, model, 'lm_head.weight')


    out_file.close()
    print(f"Exported model to {output_path}")





def export_config(model, config, output_path):
    """
    Exports the config to a C header file, following this configuration example:

        #define VOCAB_SIZE 256
        #define N_LAYER 12
        #define D_MODEL 768
        #define D_INNER 1536
        #define DT_RANK 48
        #define D_STATE 16
        #define D_CONV 4

    #define [KEY] [VALUE]
    key is converted to uppercase and value is the value from the config dictionary
    """

    vocab_size = config['vocab_size']
    rounded_vocab_size = vocab_size if vocab_size % 8 == 0 else vocab_size + (8 - (vocab_size % 8))

    with open(output_path, 'w') as f:
        f.write("#pragma once\n\n")
        f.write("#define VOCAB_SIZE %d\n" % vocab_size)
        f.write("#define ROUNDED_VOCAB_SIZE %d\n\n" % rounded_vocab_size)
        f.write("#define N_LAYER %d\n" % config['n_layer'])
        f.write("#define D_MODEL %d\n" % config['d_model'])
        f.write("#define D_INNER %d\n" % (2 * config['d_model']))
        f.write("#define DT_RANK %d\n" % model['layers.0.mixer.dt_proj.weight'].shape[1])
        f.write("#define D_STATE %d\n" % model['layers.0.mixer.A'].shape[1])
        f.write("#define D_CONV %d\n" % model['layers.0.mixer.conv1d.weight'].shape[2])


    print(f"Exported config to {output_path}")


















model = load_model('./pytorch_model.bin')
config = load_config('./config.json')

export_model(model, config, './model.q8_0.bin')
export_config(model, config, './config.h')

!mv model.q8_0.bin /content/drive/MyDrive/mamba-1.5b
