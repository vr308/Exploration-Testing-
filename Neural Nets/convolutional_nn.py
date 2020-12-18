#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 17 17:03:11 2020

@author: vr308
"""

import torch
import torchvision
import configparser
import torch.nn.functional as F
import torch.optim as optim
import os

class Net(torch.nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = torch.nn.Conv2d(1,10, kernel_size=5)
        self.conv2 = torch.nn.Conv2d(10, 20, kernel_size=5)
        self.drop_layer = torch.nn.Dropout2d()
        self.fc1 = torch.nn.Linear(320, 50)
        self.fc2 = torch.nn.Linear(50,10)
        
    def forward(self, x):
        
        x = F.relu(F.max_pool2d(self.conv1(x), 2))
        x = F.relu(F.max_pool2d(self.drop_layer(self.conv2(x)), 2))
        x = x.view(-1, 320)
        x = F.relu(self.fc1(x))
        x = F.dropout(x, training=self.training)
        x = self.fc2(x)
        return F.log_softmax(x)
    

def train(epoch):
    logging_interval = 10
    network.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        optimizer.zero_grad()
        output = network(data)
        loss = F.nll_loss(output, target)
        loss.backward()
        optimizer.step()
        if batch_idx % logging_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader), loss.item()))
            train_losses.append(loss.item())
            train_counter.append(
                (batch_idx*64) + ((epoch-1)*len(train_loader.dataset)))
            torch.save(network.state_dict(), os.getcwd() + '/results/model.pth')
            torch.save(optimizer.state_dict(), os.getcwd() + '/results/optimizer.pth')
            
def test():
      network.eval()
      test_loss = 0
      correct = 0
      with torch.no_grad():
        for data, target in test_loader:
          #print('hi')
          #import pdb; pdb.set_trace();
          output = network(data)
          test_loss += F.nll_loss(output, target, size_average=False).item()
          pred = output.data.max(1, keepdim=True)[1]
          correct += pred.eq(target.data.view_as(pred)).sum()
      test_loss /= len(test_loader.dataset)
      test_losses.append(test_loss)
      print('\nTest set: Avg. loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
        test_loss, correct, len(test_loader.dataset),
        100. * correct / len(test_loader.dataset)))

if __name__ == '__main__':
    
    parser = configparser.ConfigParser()
    parser.read('config.ini')
    
    batch_size_train = int(parser['data']['batch_size_train'])
    batch_size_test = int(parser['data']['batch_size_test'])
    
    learning_rate = float(parser['training_hypers']['learning_rate'])
    momentum = float(parser['training_hypers']['momentum'])
    n_epochs = int(parser['training_hypers']['n_epochs'])
    
    
    train_loader = torch.utils.data.DataLoader(
      torchvision.datasets.MNIST( 'MNIST_train', train=True, download=False,
                                 transform=torchvision.transforms.Compose([
                                   torchvision.transforms.ToTensor(),
                                   torchvision.transforms.Normalize(
                                     (0.1307,), (0.3081,))
                                 ])),
      batch_size=batch_size_train, shuffle=True)
    
    test_loader = torch.utils.data.DataLoader(
      torchvision.datasets.MNIST( 'MNIST_test', train=False, download=False,
                                 transform=torchvision.transforms.Compose([
                                   torchvision.transforms.ToTensor(),
                                   torchvision.transforms.Normalize(
                                     (0.1307,), (0.3081,))
                                 ])),
      batch_size=batch_size_test, shuffle=True)
    
    test_samples = enumerate(test_loader)
    batch_idx, (example_data, example_targets) = next(test_samples)
    
    network = Net()
    optimizer = optim.SGD(network.parameters(), lr = learning_rate, momentum=momentum)
    
    train_losses = []
    train_counter = []
    test_losses = []
    test_counter = [i*len(train_loader.dataset) for i in range(n_epochs + 1)]
    
    test()
    for epoch in range(1, n_epochs + 1):
        train(epoch)
        test()
        
    
    continued_network = Net()
    continued_optimizer = optim.SGD(network.parameters(), lr=learning_rate,
                                momentum=momentum)
    
    network_state_dict = torch.load(os.getcwd() + '/results/model.pth')
    continued_network.load_state_dict(network_state_dict)

    optimizer_state_dict = torch.load(os.getcwd() + '/results/optimizer.pth')
    continued_optimizer.load_state_dict(optimizer_state_dict)

    for i in range(6,8):
      test_counter.append(i*len(train_loader.dataset))
      train(i)
      test()