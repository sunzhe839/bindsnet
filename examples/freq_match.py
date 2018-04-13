import os
import sys
import torch
import numpy             as np
import argparse
import matplotlib.pyplot as plt

from time                         import time

from bindsnet.analysis.plotting   import *
from bindsnet.network             import Network
from bindsnet.encoding            import get_bernoulli

from bindsnet.network.monitors    import Monitor
from bindsnet.network.nodes       import LIFNodes, Input
from bindsnet.network.connections import Connection
from bindsnet.network.learning    import m_stdp_et

parser = argparse.ArgumentParser()
parser.add_argument('-n', type=int, default=100)
parser.add_argument('-i', type=int, default=100000)
parser.add_argument('--plot_interval', type=int, default=500)
parser.add_argument('--print_interval', type=int, default=25)
parser.add_argument('--plot', dest='plot', action='store_true')
parser.add_argument('--gpu', dest='gpu', action='store_true')
parser.set_defaults(plot=False, gpu=False, train=True)
locals().update(vars(parser.parse_args()))

sqrt = int(np.sqrt(n))

network = Network(dt=1.0)

inpt = Input(n, traces=True)
output = LIFNodes(n, traces=True)

w = 1.5*torch.rand(n, n)
conn = Connection(inpt, output, w=w, update_rule=m_stdp_et, nu=1, wmin=0, wmax=1.25)

network.add_layer(inpt, 'X')
network.add_layer(output, 'Y')
network.add_connection(conn, source='X', target='Y')

spike_monitors = {layer : Monitor(network.layers[layer], ['s']) for layer in network.layers}
for layer in spike_monitors:
	network.add_monitor(spike_monitors[layer], '%s' % layer)

data = torch.rand(i, n)
loader = get_bernoulli(data, time=1, max_prob=0.05)

reward = 0
a_plus = 1
a_minus = 0

rewards = []

avg_rates = torch.zeros(n)
target_rates = 0.02 + torch.rand(n) / 20

spike_record = {layer : torch.zeros(plot_interval, n) for layer in network.layers}

print()
for i in range(i):
	inpts = {'X' : next(loader)}
	kwargs = {'reward' : reward, 'a_plus' : a_plus, 'a_minus' : a_minus}
	network.run(inpts, 1, **kwargs)
	
	spikes = {layer : spike_monitors[layer].get('s').view(-1) for layer in spike_monitors}
	for layer in spike_record:
		spike_record[layer][i % plot_interval] = spikes[layer]
	
	if i == 0:
		avg_rates = spikes['Y']
	else:
		avg_rates = ((i - 1) / i) * avg_rates + (1 / i) * spikes['Y']
	
	reward = -(avg_rates - target_rates)
	rewards.append(reward.sum())
	
	if i % print_interval == 0:
		print('Averaged reward (iteration %d):' % i, reward.sum())
		
	
	for m in spike_monitors:
		spike_monitors[m]._reset()
	
	if plot:
		if i == 0:
			spike_ims, spike_axes = plot_spikes(spike_record)
			weights_im = plot_weights(conn.w.view(n, n))

			fig, ax = plt.subplots()
			im = ax.matshow(torch.stack([avg_rates, target_rates]), cmap='hot_r')

			ax.set_xticks(()); ax.set_yticks(())
			ax.set_aspect('auto')
			
			fig2, ax2 = plt.subplots()
			line2, = ax2.plot(np.abs(rewards))
			ax2.axhline(0, ls='--', c='r')
			
			ax2.set_title('Absolute value of averaged "punishment" over time')
			ax2.set_xlabel('Timesteps')
			ax2.set_ylabel('Abs. value punishment')
			
			plt.pause(1e-8)

		elif i % plot_interval == 0:
			spike_ims, spike_axes = plot_spikes(spike_record, spike_ims, spike_axes)
			weights_im = plot_weights(conn.w.view(n, n), im=weights_im)

			im.set_data(torch.stack([avg_rates, target_rates]))
			
			line2.set_xdata(range(len(rewards)))
			line2.set_ydata(np.abs(rewards))
			
			ax2.relim() 
			ax2.autoscale_view(True, True, True) 

			plt.pause(1e-8)