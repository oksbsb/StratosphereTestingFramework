# Part of this file was taken from Viper - https://github.com/botherder/viper
# The rest is from the Stratosphere Testing Framework
# See the file 'LICENSE' for copying permission.

# This module implements markov chains of first order over the letters in the chain of states of the behavioral models.
import persistent
import pykov
import BTrees.OOBTree
from subprocess import Popen, PIPE
import copy
import re
import numpy as np
import tempfile
import cPickle
import math
import numpy

from stf.common.out import *
from stf.common.abstracts import Module
from stf.core.models import  __groupofgroupofmodels__ 
from stf.core.labels import __group_of_labels__
from stf.core.database import __database__
import stf.common.markov_chains as mc





#################
#################
#################
class Markov_Model(persistent.Persistent):
    """ This class is the actual markov model of second order to each label"""
    def __init__(self, id):
        self.mm_id = id
        self.state = ""
        self.label_id = -1
        self.connections = BTrees.OOBTree.BTree()
        self.trained_threshold = -1

    def get_threshold(self):
        try:
            return self.trained_threshold
        except AttributeError:
            return False

    def set_threshold(self, threshold):
        self.trained_threshold = threshold

    def get_id(self):
        return self.mm_id

    def set_id(self, id):
        self.mm_id = id

    def get_state(self):
        return self.state

    def set_state(self, state):
        self.state = state

    def get_label_id(self):
        return self.label_id

    def set_label_id(self, label_id):
        self.label_id = label_id

    def get_connections(self):
        return self.connections
    
    def set_connections(self, connections):
        # Use deepcopy so we store a copy of the connections and not the connections themselves. This is needed because more connections can be added to the label, however the state in this markov chain will miss them. Also because the original connections can be deleted
        self.connections = copy.deepcopy(connections)

    def set_self_probability(self, prob):
        """ Set the probability of detecting itself """
        self.self_probability = prob

    def get_self_probability(self):
        try:
            return self.self_probability
        except AttributeError:
            return False

    def count_connections(self):
        """ Return the amount of connections in the markov model """
        count = 0
        for id in self.connections:
            for conn in self.connections[id]:
                count += 1
        return count

    def get_init_vector(self):
        return self.init_vector

    def set_matrix(self, matrix):
        self.matrix = matrix

    def get_matrix(self):
        return self.matrix

    def create(self, states):
        """ Create the Markov chain itself. We use the parameter instead of the attribute so we can compute the matrix for different states """
        # Separete the letters considering the letter and the symbol as a unique state:
        # So from "88,a,b," we get: '8' '8,' 'a,' 'b,'
        try:
            # This is a first order markov model. Each individual object (letter, number, etc.) is a state
            separated_letters = list(states)
        except AttributeError:
            print_error('There is no state yet')
            return False
        # Generate the MC
        # Deprecated pykov
        #self.init_vector, self.matrix = pykov.maximum_likelihood_probabilities(separated_letters, lag_time=1, separator='#')
        # Mimicking old version where a state is any letter
        new_states = self.get_old_first_order_states(states)
        # New states where we differentiate how they were created
        #new_states = self.get_new_first_order_states(states)
        self.init_vector, self.matrix = mc.maximum_likelihood_probabilities(new_states, order=1)

    def get_old_first_order_states(self, states):
        """ Get the first order states """
        return list(states)

    def get_new_first_order_states(self, states):
        """ Get the first order states """
        #print 'Receiving to analyze: {} (len {})'.format(states, len(states))
        #raw_input()
        # Help functions
        def is_letter(state):
            try:
                if str(state) in 'abcdefghiABCDEFGHIrstuvwxyzRSTUVWXYZ':
                    return True
                else:
                    return False
            except ValueError:
                return False

        def is_number_19(state):
            try:
                if int(state) != 0:
                    return True
                else:
                    return False
            except ValueError:
                return False

        def is_zero(state):
            try:
                if int(state) == 0:
                    return True
                else:
                    return False
                return True
            except ValueError:
                return False

        def is_symbol(state):
            if str(state) in '.,+*':
                return True
            else:
                return False
        # End help functions

        new_states = []
        # The first number is always a state by itself. It is considered to have an empty symbol.
        if is_number_19(states[0]) and is_number_19(states[1]):
            new_states.append(states[0])
            print 'New states so far: {}'.format(new_states)
            # Take the first letter out
            i = 1 # i is the start of the next state in the string
            while i < len(states):
                # It must follow a number19 or letter
                if is_number_19(states[i]) or is_letter(states[i]):
                    # Get the symbol
                    if is_symbol(states[ i + 1]):
                        new_states.append(''.join(states[ i : i + 2]))
                        # Update i to the next index after this state finished
                        i = i + 2
                    elif is_zero(states[ i + 1]):
                        j = i
                        while is_zero(states[ j + 1 ]):
                            j += 1
                        new_states.append(''.join(states[ i : j + 1 ]))
                        # Update i to the next index after this state finished
                        i = j + 1
                else:
                    print 'Warning. We should not have these combination of letters in the state.'
                    return False
                #print 'New states so far: {}'.format(new_states)
                #raw_input()
            # End while
        else:
            # The first two states are not numbers, broken states?
            print 'Warning. Not sure we should be here. The state started without numbers.'
            return False
        return new_states

    def get_matrix(self):
        """ Return the matrix """
        return self.matrix

    def print_matrix(self):
        print_info('Matrix of the Markov Model {}'.format(self.get_id()))
        for first in self.matrix:
            print first, self.matrix[first]

    def simulate(self, amount):
        print type(self.matrix.walk(5))
        """ Generate a simulated chain using this markov chain """
        chain = ''
        chain += state[0]
        chain += state[1]
        chain += state[2]
        chain += ''.join(self.matrix.walk(amount))
        print chain
        return True

    ####################################
    ####################################
    def compute_probability(self, state):
        """ Given a chain of letters, return the probability that it was generated by this MC """
        i = 0
        probability = 0
        ignored = 0
        # Get the initial probability of this letter in the IV.
        try:
            init_letter_prob = math.log(self.init_vector[state[i]])
        except ValueError:
            # There is not enough data to even create a matrix
            init_letter_prob = 0
        except IndexError:
            # The first letter is not in the matrix, so penalty...
            init_letter_prob = -4.6
        # We should have more than 2 states at least
        while i < len(state) and len(state) > 1:
            try:
                vector = state[i] + state[i+1]
                growing_v = state[0:i+2]
                # The transitions that include the # char will be automatically excluded
                temp_prob = self.matrix.walk_probability(vector)
                i += 1
                if temp_prob != float('-inf'):                
                    probability = probability + temp_prob # logs should be summed up
                    #print_info('\tTransition [{}:{}]: {} -> Prob:{:.10f}. CumProb: {}'.format(i-1, i,vector, temp_prob, probability))
                else:
                    # Here is our trick. If two letters are not in the matrix... assign a penalty probability
                    # The temp_prob is the penalty we assign if we can't find the transition
                    temp_prob = -4.6 # Which is approx 0.01 probability
                    probability = probability + temp_prob # logs should be +
                    if '#' not in vector:
                        ignored += 1
                    continue
            except IndexError:             
                # We are out of letters        
                break
        #if ignored:
            #print_warning('Ignored transitions: {}'.format(ignored))
            #ignored = 0
        return probability       

    def export(self, path):
        """ Export the current model to that path """
        final_file = path + str(self.get_label().get_name()) + '-' + str(self.get_id()) + '.stfm'
        output = open(final_file, 'wb')
        cPickle.dump(self.init_vector,output)         
        cPickle.dump(self.matrix,output)         
        cPickle.dump(self.get_state(),output)         
        cPickle.dump(self.get_self_probability(),output)         
        cPickle.dump(self.get_label().get_name(),output)         
        cPickle.dump(self.get_threshold(),output)         
        output.close()

    def get_label(self):
        """ Return the label name"""
        label = __group_of_labels__.get_label_by_id(self.get_label_id())
        if label:
            label_name = label.get_name()
        else:
            print_error('The label used in the markov model {} does not exist anymore. You should delete the markov chain manually (The markov chain {} does not appear in the following list).'.format(self.get_id(), self.get_id()))
        return label
            
    def __repr__(self):
        label = __group_of_labels__.get_label_by_id(self.get_label_id())
        if label:
            label_name = label.get_name()
        else:
            label_name = 'Deleted'
        #current_connections = label.get_connections_complete()
        response = "Id:"+str(self.get_id())+", Label: "+label_name+", State Len:"+str(len(self.get_state()))+", #Conns:"+str(self.count_connections())+", First 50 states: "+self.get_state()[0:50]
        return(response)



######################
######################
######################
class Group_of_Markov_Models_2(Module, persistent.Persistent):
    cmd = 'markov_models_2'
    description = 'This module implements markov chains of second order over the letters in the chains of states in a LABEL. ' + yellow('Warning') + ', if the original models or labels are deleted, you should fix these models by hand.'
    authors = ['Sebastian Garcia']
    # Markov Models main dictionary
    markov_models = BTrees.OOBTree.BTree()

    # Mandatory Method!
    def __init__(self):
        # Call to our super init
        super(Group_of_Markov_Models_2, self).__init__()
        self.parser.add_argument('-l', '--list', action='store_true', help='List the markov models already applied. You can use a filter with -f.')
        self.parser.add_argument('-g', '--generate', metavar='generate', help='Generate the markov chain for this label. Give label name.')
        self.parser.add_argument('-m', '--printmatrix', metavar='printmatrix', help='Print the markov chains matrix of the given markov model id.')
        self.parser.add_argument('-S', '--simulate', metavar='simulate', help='Use this markov chain to generate a new simulated chain of states. Give the markov chain id. The length is now fixed in 100 states.')
        self.parser.add_argument('-d', '--delete', metavar='delete', help='Delete this markov chain. Give the markov chain id.')
        self.parser.add_argument('-p', '--printstate', metavar='printstate', help='Print the chain of states of all the models included in this markov chain. Give the markov chain id.')
        self.parser.add_argument('-r', '--regenerate', metavar='regenerate', help='Regenerate the markov chain. Usually because more connections were added to the label. Give the markov chain id.')
        self.parser.add_argument('-a', '--generateall', action='store_true', help='Generate the markov chain for all the labels that don\'t have one already')
        self.parser.add_argument('-f', '--filter', metavar='filter', nargs = '+', default="", help='Filter the markov models. For example for listing. Keywords: name, id. Usage: name=<text> name!=<text> or id=23. Partial matching.')
        self.parser.add_argument('-n', '--numberoffflows', metavar='numberofflows', default="3", help='When creating the markov models, this is the minimum number of flows that the connection should have. Less than this and the connection will be ignored. Be default 3.')
        self.parser.add_argument('-t', '--train', metavar='markovmodelid', help='Train the distance threshold for this Markov Model Id. Use -f to filter the list of Markov Models to use in the training or use -i to specify a list of markov models id.')
        self.parser.add_argument('-i', '--train_ids', metavar='train_ids', default="", help='Specify the Ids of the markov models to use. Can be used together with -t and -T. You can specify a singled id or a comma separated list. You can use \'all\' to specify all the models.')
        self.parser.add_argument('-v', '--verbose', metavar='verbose_val', default=0, type=int, help='Make the train process more verbose, printing the details of the models matched. Give an integer value.')
        self.parser.add_argument('-T', '--threshold', metavar='threshold', type=float, help='Change the threshold of a markov model to this value. Use -i to designate the ids of target markov models.')
        self.parser.add_argument('-e', '--export', metavar='model_id', type=int, help='Export the given markov model id to an object on disk. Give the model id here. You must use -E to give an export path.')
        self.parser.add_argument('-E', '--exportpath', metavar='path', type=str, help='The folder path were to export the markov model.')

    # Mandatory Method!
    def get_name(self):
        """ Return the name of the module"""
        return self.cmd

    # Mandatory Method!
    def get_main_dict(self):
        """ Return the main dict where we store the info. Is going to the database"""
        return self.markov_models

    # Mandatory Method!
    def set_main_dict(self, dict):
        """ Set the main dict where we store the info. From the database"""
        self.markov_models = dict

    def get_markov_model_by_label_id(self, id):
        """ Search a markov model by label id """
        for markov_model in self.get_markov_models():
            if markov_model.get_label_id() == id:
                # Shouldn't this be the model returned?
                return True
        return False

    def get_markov_model(self, id):
        try:
            return self.markov_models[id]
        except KeyError:
            return False

    def get_markov_models(self):
        return self.markov_models.values()

    def print_matrix(self, markov_model_id):
        try:
            self.markov_models[int(markov_model_id)].print_matrix()
        except KeyError:
            print_error('That markov model id does not exists.')

    def construct_filter(self, filter):
        """ Get the filter string and decode all the operations """
        # If the filter string is empty, delete the filter variable
        if not filter:
            try:
                del self.filter 
            except:
                pass
            return True
        self.filter = []
        # Get the individual parts. We only support and's now.
        for part in filter:
            # Get the key
            try:
                key = re.split('<|>|=|\!=', part)[0]
                value = re.split('<|>|=|\!=', part)[1]
            except IndexError:
                # No < or > or = or != in the string. Just stop.
                break
            try:
                part.index('<')
                operator = '<'
            except ValueError:
                pass
            try:
                part.index('>')
                operator = '>'
            except ValueError:
                pass
            # We should search for != before =
            try:
                part.index('!=')
                operator = '!='
            except ValueError:
                # Now we search for =
                try:
                    part.index('=')
                    operator = '='
                except ValueError:
                    pass
            self.filter.append((key, operator, value))

    def apply_filter(self, model):
        """ Use the stored filter to know what we should match"""
        responses = []
        try:
            self.filter
        except AttributeError:
            # If we don't have any filter string, just return true and show everything
            return True
        # Check each filter
        for filter in self.filter:
            key = filter[0]
            operator = filter[1]
            value = filter[2]
            if key == 'name':
                # For filtering based on the label assigned to the model with stf (contrary to the flow label)
                label = model.get_label()
                try:
                    labelname = label.get_name()
                except AttributeError:
                    # Label was deleted
                    labelname = False
                    responses.append(False)
                    continue
                if operator == '=':
                    if value in labelname:
                        responses.append(True)
                    else:
                        responses.append(False)
                elif operator == '!=':
                    if value not in labelname:
                        responses.append(True)
                    else:
                        responses.append(False)
            elif key == 'id':
                id = int(model.get_id())
                value = int(value)
                if operator == '=':
                    if value == id:
                        responses.append(True)
                    else:
                        responses.append(False)
                elif operator == '!=':
                    if value != id:
                        responses.append(True)
                    else:
                        responses.append(False)
            elif key == 'statelength':
                state = model.get_state()
                if operator == '<':
                    if len(state) < int(value):
                        responses.append(True)
                    else:
                        responses.append(False)
                elif operator == '>':
                    if len(state) > int(value):
                        responses.append(True)
                    else:
                        responses.append(False)
                elif operator == '=':
                    if len(state) == int(value):
                        responses.append(True)
                    else:
                        responses.append(False)
            else:
                return False

        for response in responses:
            if not response:
                return False
        return True

    def list_markov_models(self, filter):
        self.construct_filter(filter)
        all_text = 'Second Order Markov Models\n'
        all_text += ' Id  | State Len | # Conn | Label \t\t\t\t       | Needs Regen? | Thres | First 100 Letters in State\n'
        for markov_model in self.get_markov_models():
            if self.apply_filter(markov_model):
                label = markov_model.get_label()
                if not label:
                    label_name = 'Deleted'
                    current_connections = 'Unknown'
                else:
                    label_name = label.get_name()
                    current_connections = label.get_connections_complete()
                needs_regenerate = True
                # Do we need to regenerate this mc?
                if current_connections == markov_model.get_connections():
                    needs_regenerate = False
                all_text += '{: < 5} | {: > 7} | {} | {:50} | {} | {:3} | {}\n'.format(markov_model.get_id(), len(markov_model.get_state()), markov_model.count_connections(), label_name, needs_regenerate, markov_model.get_threshold(), markov_model.get_state()[0:100])
        # Print with less
        f = tempfile.NamedTemporaryFile()
        f.write(all_text)
        f.flush()
        p = Popen('less -R ' + f.name, shell=True, stdin=PIPE)
        p.communicate()
        sys.stdout = sys.__stdout__ 
        f.close()

    def create_new_model(self, label_name, number_of_flows):
        """ Given a label name create a new markov chain object"""
        # Get the label object
        label_to_model = __group_of_labels__.get_label(label_name)
        if label_to_model:
            # Create a new markov chain object
            ## Get the new id
            try:
                mm_id = self.markov_models[list(self.markov_models.keys())[-1]].get_id() + 1
            except (KeyError, IndexError):
                mm_id = 1
            markov_model = Markov_Model(mm_id)
            # Store the label id
            markov_model.set_label_id(label_to_model.get_id())
            state = ""
            # Get all the connections in the label
            connections = label_to_model.get_connections_complete()
            # Get all the group of models and connections names
            for group_of_model_id in connections:
                # Get all the connections
                for conn in connections[group_of_model_id]:
                    # Get the model group
                    group = __groupofgroupofmodels__.get_group(group_of_model_id)
                    # Get the model
                    model = group.get_model(conn)
                    # Get each state
                    #state += model.get_state() + '#'
                    state += model.get_state() 
            # Delete the last #
            #state = state[:-1]
            # Store the state
            markov_model.set_state(state)
            # Store the connections
            markov_model.set_connections(connections)
            # Create the MM itself
            markov_model.create(markov_model.get_state())
            # Generate the self probability
            prob = markov_model.compute_probability(markov_model.get_state())
            markov_model.set_self_probability(prob)
            # Store
            self.markov_models[mm_id] = markov_model
            print_info('New model created with id {}'.format(markov_model.get_id()))
        else:
            print_error('No label with that name')

    def simulate(self, markov_model_id):
        """ Generate a new simulated chain of states for this markov chain """
        try:
            markov_model = self.get_markov_model(int(markov_model_id))
            markov_model.simulate(100)
        except KeyError:
            print_error('No such markov model id')

    def delete(self, markov_model_id):
        """ Delete the markvov chain """
        try:
            if '-' in markov_model_id:
                # There is a range
                start = int(markov_model_id.split('-')[0])
                end = int(markov_model_id.split('-')[1])
                for temp_id in range(start, end + 1):
                    try:
                        self.markov_models.pop(temp_id)
                    except KeyError:
                        print_error('No such markov model id, continuing...')
            elif ',' in markov_model_id:
                for temp_id in markov_model_id.split(','):
                    self.markov_models.pop(int(temp_id))
            else:
                self.markov_models.pop(int(markov_model_id))
        except KeyError:
            print_error('No such markov model id')

    def printstate(self, markov_model_id):
        """ Print all the info about the markov chain """
        try:
            markov_model = self.get_markov_model(int(markov_model_id))
        except KeyError:
            print_error('No such markov model id')
            return False
        print_info('Markov Chain ID {}'.format(markov_model_id))
        print_info('Label')
        try:
            label_name = __group_of_labels__.get_label_name_by_id(markov_model.get_label_id())
        except AttributeError:
            print_error('The id does not exists.')
            return False
        print '\t', 
        print_info(label_name)
        state = markov_model.get_state()
        print_info('Len of State: {} (Max chars printed: 2000)'.format(len(state)))
        print '\t', 
        print_info(state[0:2000])
        print_info('Connections in the Markov Chain')
        connections = markov_model.get_connections()
        print '\t', 
        print_info(connections)
        # Plot the histogram of letters
        print_info('Histogram of Amount of Letters')
        dist_path,error = Popen('bash -i -c "type distribution"', shell=True, stderr=PIPE, stdin=PIPE, stdout=PIPE).communicate()
        if not error:
            distribution_path = dist_path.split()[0]
            list_of_letters = ''.join([i+'\n' for i in list(state)])[0:65535]
            print 'Key=Amount of letters (up to the first 65536 letters)'
            Popen('echo \"' + list_of_letters + '\" |distribution --height=50 | sort -nk1', shell=True).communicate()
        else:
            print_error('For ploting the histogram we use the tool https://github.com/philovivero/distribution. Please install it in the system to enable this command.')
        #print_info('Test Probability: {}'.format(markov_model.compute_probability("r*R*")))
        log_self_prob = markov_model.compute_probability(markov_model.get_state())
        print_info('Log Probability of detecting itself: {}'.format(log_self_prob))

    def regenerate(self, markov_model_id):
        """ Regenerate the markvov chain """
        try:
            markov_model = self.get_markov_model(int(markov_model_id))
        except KeyError:
            print_error('No such markov model id')
            return False
        label = __group_of_labels__.get_label_by_id(markov_model.get_label_id())
        connections = label.get_connections_complete()
        # Get all the group of models and connections names
        state = ""
        for group_of_model_id in connections:
            # Get all the connections
            for conn in connections[group_of_model_id]:
                # Get the model group
                group = __groupofgroupofmodels__.get_group(group_of_model_id)
                # Get the model
                model = group.get_model(conn)
                # Get each state
                state += model.get_state() + '#'
        # Delete the last #
        state = state[:-1]
        # Store the state
        markov_model.set_state(state)
        # Store the connections
        markov_model.set_connections(connections)
        # Create the MM itself
        markov_model.create(markov_model.get_state())
        print_info('Markov model {} regenerated.'.format(markov_model_id))
####
    def generate_all_models(self, number_of_flows):
        """ Read all the labels and generate all the markov models if they dont already have one """
        labels = __group_of_labels__.get_labels()
        for label in labels:
            if not self.get_markov_model_by_label_id(label.get_id()):
                # We dont have it
                self.create_new_model(label.get_name(), number_of_flows)

    def compute_errors(self, train_label, test_label):
        """ Get the train and test labels and figure it out the errors. A TP is when we detect CC not Botnet."""
        errors = {}
        errors['TP'] = 0.0
        errors['TN'] = 0.0
        errors['FN'] = 0.0
        errors['FP'] = 0.0
        # So we can work with multiple positives and negative labels
        if 'Botnet' in train_label or 'Malware' in train_label:
            train_label_positive = True
        elif 'Normal' in train_label:
            train_label_positive = False
        if 'Botnet' in test_label or 'Malware' in test_label:
            test_label_positive = True
        elif 'Normal' in test_label:
            test_label_positive = False

        if train_label_positive and test_label_positive:
            errors['TP'] += 1
        elif train_label_positive and not test_label_positive:
            errors['FP'] += 1
        elif not train_label_positive and not test_label_positive:
            errors['TN'] += 1
        elif not train_label_positive and test_label_positive:
            errors['FN'] += 1
        return errors

    def compute_error_metrics(self, sum_errors):
        """ Given the sum up errors, compute the performance metrics """
        TP = sum_errors['TP']
        TN = sum_errors['TN']
        FN = sum_errors['FN']
        FP = sum_errors['FP']
        """ Get the errors and compute the metrics """
        metrics = {}
        # The order is important, because later we sort based on the order. More important to take a decision should be up
        # The fallback to inf or -inf depends if the metric is _good_ up or _good_ down. Should be the opposite.
        try:
            metrics['FMeasure1'] = 2 * TP / ((2 * TP) + FP + FN)
        except ZeroDivisionError:
            metrics['FMeasure1'] = float('-Inf')
        try:
            metrics['FPR'] = FP / (FP + TN) 
        except ZeroDivisionError:
            metrics['FPR'] = float('Inf')
        try:
            metrics['TPR'] = TP / (TP + FN)
        except ZeroDivisionError:
            metrics['TPR'] = float('-Inf')
        try:
            metrics['FNR'] = FN / (TP + FN)
        except ZeroDivisionError:
            metrics['FNR'] = float('Inf')
        try:
            metrics['TNR'] = TN / (TN + FP)
        except ZeroDivisionError:
            metrics['TNR'] = float('-Inf')
        try:
            metrics['Precision'] = TP / (TP + FN)
        except ZeroDivisionError:
            metrics['Precision'] = float('-Inf')
        try:
            # False discovery rate
            metrics['FDR'] = FP / (TP + FP)
        except ZeroDivisionError:
            metrics['FDR'] = float('Inf')
        try:
            # Positive Predicted Value
            metrics['PPV'] = TP / (TP + FP)
        except ZeroDivisionError:
            metrics['PPV'] = float('-Inf')
        try:
            # Negative Predictive Value
            metrics['NPV'] = TN / (TN + FN)
        except ZeroDivisionError:
            metrics['NPV'] = float('-Inf')
        try:
            metrics['Accuracy'] = (TP + TN) / (TP + TN + FP + FN)
        except ZeroDivisionError:
            metrics['Accuracy'] = float('-Inf')
        try:
            # Positive likelihood ratio
            metrics['PLR'] = metrics['TPR'] / metrics['FPR']
        except ZeroDivisionError:
            metrics['PLR'] = float('-Inf')
        try:
            # Negative likelihood ratio
            metrics['NLR'] = metrics['FNR'] / metrics['TNR']
        except ZeroDivisionError:
            metrics['NLR'] = float('-Inf')
        try:
            # Diagnostic odds ratio
            metrics['DOR'] = metrics['PLR'] / metrics['NLR']
        except ZeroDivisionError:
            metrics['DOR'] = float('-Inf')
        # Store the sums
        metrics['TP'] = TP
        metrics['TN'] = TN
        metrics['FN'] = FN
        metrics['FP'] = FP
        return metrics

    def sum_up_errors(self, vector):
        """ Given a vector of values, sum up the errors """
        sum_errors = {}
        sum_errors['TP'] = 0.0
        sum_errors['TN'] = 0.0
        sum_errors['FN'] = 0.0
        sum_errors['FP'] = 0.0
        for i in vector:
            errors = i['Errors']
            sum_errors['TP'] += errors['TP']
            sum_errors['TN'] += errors['TN']
            sum_errors['FN'] += errors['FN']
            sum_errors['FP'] += errors['FP']
        return sum_errors

    def train(self, model_id_to_train, filter, test_ids, verbose):
        """ Train the distance threshold of a model. The models to train with can be determined by the filter or by a list of comma separated ids """
        # Create the filter and the list of ids
        if filter and test_ids == "":
            self.construct_filter(filter)
            test_models_ids = []
        # If we don't have a filter, maybe the user specified a list of models ids to match
        elif test_ids != "" and not filter:
            # When calling directly markov_model is a string
            if type(test_ids) == str:
                if test_ids == 'all':
                    # If all was specified, create a range with all of them
                    test_ids = range(0,len(self.get_markov_models()))
                elif ',' in test_ids:
                    test_models_ids = map(int, test_ids.split(','))
                else:
                    # We need a vector, so just create it with the same id
                    test_models_ids = [int(test_ids), int(test_ids)]
            # When calling this function from other modules, can be a vector
            else:
                test_models_ids = map(int, test_ids)
        else:
            print_error('No test ids were specified using a filter OR a number. Dont specify both.')
            return False
        train_model = self.get_markov_model(model_id_to_train)
        # Check that the train model id exists
        try:
            train_model_id = train_model.get_id()
        except AttributeError:
            print_error('No such training id is available')
            return False
        if verbose > 1:
            print_info('Training model: {}. Amount of letters used for training: {}'.format(train_model, 100)) # The 100 is hardcoded. See the number below.
        # To store the training data
        thresholds_train = {}
        for test_model in self.get_markov_models():
            # Check that the models exist
            try:
                test_model_id = test_model.get_id()
            except AttributeError:
                print_error('No such testing id is available')
                return False
            # Get the labels from the models
            try:
                train_label = train_model.get_label().get_name()
                test_label = test_model.get_label().get_name()
            except AttributeError:
                # The model was deleted. Ignore this and continue
                continue
            # Get the protocols for the labels
            try:
                train_protocol = train_label.split('-')[2]
            except IndexError:
                # The label is not complete, maybe because now is "Deleted". Ignore
                return False
            try:
                test_protocol = test_label.split('-')[2]
            except IndexError:
                # The label is not complete, maybe because now is "Deleted". Ignore
                return False
            # Apply the filter and avoid training with itself and only if the protocols match
            if ( (filter != "" and self.apply_filter(test_model)) or (test_models_ids != "" and test_model_id in test_models_ids)) and test_model_id != train_model_id and train_protocol == test_protocol:
                if verbose > 1:
                    print_info('\tTraining with model {}'.format(test_model))
                # Store info about this particular test training. Later stored within the threshold vector
                train_vector = {}
                train_vector['ModelId'] = test_model_id
                if verbose:
                        print '\t', test_model
                # For each threshold to train
                # Now we go from 1.1 to 2
                exit_threshold_for = False
                for threshold in np.arange(1.1,2.1,0.1):
                    # Store the original matrix and prob for later
                    original_matrix = train_model.get_matrix()
                    original_self_prob = test_model.get_self_probability()
                    # For each test state
                    index = 0
                    while index < len(test_model.get_state()):
                        # Get the states so far
                        train_sequence = train_model.get_state()[0:index+1]
                        test_sequence = test_model.get_state()[0:index+1]
                        # First re-create the matrix only for this sequence
                        train_model.create(train_sequence)
                        # Prob of the states so far
                        train_prob = float(train_model.compute_probability(train_sequence))
                        test_prob = float(train_model.compute_probability(test_sequence))
                        # Compute distance
                        if train_prob < test_prob:
                            try:
                                distance = train_prob / test_prob
                            except ZeroDivisionError:
                                distance = -1
                        elif train_prob > test_prob:
                            try:
                                distance = test_prob / train_prob
                            except ZeroDivisionError:
                                distance = -1
                        elif train_prob == test_prob:
                            distance = 1
                        # Is distance < threshold? We found a good match.
                        # index > 3 means that we discard the matching of the first three letters, because we don't have a letter with periodicity yet.
                        if index > 3 and distance < threshold and distance > 0:
                            # Compute the errors: TP, TN, FP, FN
                            errors = self.compute_errors(train_label, test_label)
                            if verbose > 1:
                                print '\t\tTraining with threshold: {}. Distance: {}. Errors: {}'.format(threshold, distance, errors)
                            # Store the info, if it matched, for each letter in the test state
                            train_vector['Distance'] = distance
                            train_vector['IndexFlow'] = index
                            train_vector['Errors'] = errors
                            # Get the old vector for this threshold
                            try:
                                prev_threshold = thresholds_train[threshold]
                            except KeyError:
                                # First time for this threshold
                                thresholds_train[threshold] = []
                                prev_threshold = thresholds_train[threshold]
                            # Store this train vector in the threshold vectors
                            prev_threshold.append(train_vector)
                            thresholds_train[threshold] = prev_threshold
                            # Tell the threshold for to exit. Means that we matched something
                            # This is never working, ... should we put it out? What was the idea? Not to try all the thresholds?
                            exit_threshold_for = False
                            # Exit the test chain of state evaluation. We don't compare more letters.
                            break
                        # Next letter
                        index += 1
                        # Put a limit in the amount of letters by now. VERIFY THIS
                        if index > 100:
                            #print_warning('Now we are limiting the maximum amount of letters in each string of every model during training to  100')
                            break
                    if exit_threshold_for:
                        # We are going to stop computing the threshold for this test model because we found one.
                        break
        # After finishing wiht all the test models...
        # Compute the error metrics for each threshold
        final_errors_metrics = {}
        for threshold in thresholds_train:
            # 1st sum up together all the errors for this threshold
            sum_errors = self.sum_up_errors(thresholds_train[threshold])
            # Compute the metrics
            metrics = self.compute_error_metrics(sum_errors)
            final_errors_metrics[threshold] = metrics 
        # Sort according to hierarchy shown
        sorted_metrics = sorted(final_errors_metrics.items(), key=lambda x: (x[1]['FMeasure1'], -x[1]['FPR'], x[1]['TPR'], x[1]['PPV'], x[1]['NPV'], x[1]['TP'], x[1]['TN'], -x[1]['FP'], -x[1]['FN'], x[1]['Precision'], -x[0]), reverse=True)
        criteria='FMeasure1'
        best_criteria = float('-Inf')
        # We can have multiple 'best' so find them all
        for threshold in sorted_metrics:
            current_criteria = threshold[1][criteria]
            # Only  print the best FM1s
            if current_criteria >= best_criteria:
                if verbose > 2:
                    print '\t\tThreshold {}: FM1:{:.3f}, FPR:{:.3f}, TPR:{:.3f}, TNR:{:.3f}, FNR:{:.3f}, PPV:{:.3f}, NPV:{:.3f}, Prec:{:.3f}, TP:{}, FP:{}, TN:{}, FN:{}'.format(threshold[0], threshold[1]['FMeasure1'], threshold[1]['FPR'], threshold[1]['TPR'], threshold[1]['TNR'], threshold[1]['FNR'], threshold[1]['PPV'], threshold[1]['NPV'], threshold[1]['Precision'], threshold[1]['TP'], threshold[1]['FP'], threshold[1]['TN'], threshold[1]['FN'])
                best_criteria = current_criteria
        # Store the trained threshold for this model
        try:
            train_model.set_threshold(sorted_metrics[0][0])
            if verbose:
                print '\tSelected: {}'.format(red(sorted_metrics[0][0]))
        except IndexError:
            train_model.set_threshold(-1)
            if verbose > 1:
                print '\tSelected: None. No other models matched.'
        return train_model.get_threshold()

    def assign_threshold_to_id(self, ids, threshold):
        """ Assign the threshold to the markov models ids"""
        # ids can be a single id, a range or 'all'
        if type(ids) == str and 'all' in ids:
            ids = range(0,len(self.get_markov_models()))
        elif type(ids) == str and ',' in ids:
            ids = map(int, ids.split(','))
        elif type(ids) == str and '-' in ids:
            first = int(ids.split('-')[0])
            last = int(ids.split('-')[1])
            ids = range(first,last + 1)
        else:
            ids = [ids]
        for id in ids:
            markov_model = self.get_markov_model(int(id))
            try:
                markov_model.set_threshold(threshold)
            except AttributeError:
                print_error('Model id {} does not exists. Continuing...'.format(id))

    def export_model(self, model_id, path):
        """ Get a model id and path, and export that model there """
        model = self.get_markov_model(model_id)
        model.export(path)

    # The run method runs every time that this command is used
    def run(self):
        # Register the structure in the database, so it is stored and use in the future. 
        if not __database__.has_structure(Group_of_Markov_Models_2().get_name()):
            print_info('The structure is not registered.')
            __database__.set_new_structure(Group_of_Markov_Models_2())
        else:
            main_dict = __database__.get_new_structure(Group_of_Markov_Models_2())
            self.set_main_dict(main_dict)

        # List general help. Don't modify.
        def help():
            self.log('info', self.description)

        # Run
        super(Group_of_Markov_Models_2, self).run()
        if self.args is None:
            return
        
        # Process the command line
        if self.args.list:
            self.list_markov_models(self.args.filter)
        elif self.args.generate:
            try:
                self.create_new_model(self.args.generate, self.args.numberofflows)
            except AttributeError:
                numberofflows = 3
                self.create_new_model(self.args.generate, numberofflows)
        elif self.args.printmatrix:
            self.print_matrix(self.args.printmatrix)
        elif self.args.simulate:
            self.simulate(self.args.simulate)
        elif self.args.delete:
            self.delete(self.args.delete)
        elif self.args.printstate:
            self.printstate(self.args.printstate)
        elif self.args.regenerate:
            self.regenerate(self.args.regenerate)
        elif self.args.train:
            if '-' in self.args.train:
                # There is a range of ids to train
                first = int(self.args.train.split('-')[0])
                last = int(self.args.train.split('-')[1])
                train_ids = range(first,last + 1)
            else:
                train_ids = [self.args.train]
            for train_id in train_ids:
                self.train(int(train_id), self.args.filter, self.args.train_ids, self.args.verbose)
        elif self.args.generateall:
            try:
                self.create_new_model(self.args.generate, self.args.numberofflows)
            except AttributeError:
                numberofflows = 3
                self.generate_all_models(numberofflows)
        elif self.args.export and self.args.exportpath:
            self.export_model(self.args.export, self.args.exportpath)
        elif self.args.threshold:
            if not self.args.train_ids:
                print_error('You must specify some markov model id to apply the threshold.')
                return False
            self.assign_threshold_to_id(self.args.train_ids, self.args.threshold)

__group_of_markov_models__ = Group_of_Markov_Models_2()
