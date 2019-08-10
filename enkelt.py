# coding=utf-8

import sys
import subprocess
import os


def run_enkelt(to_run, variables):
	global run_command
	
	run_command = run_command + str([','.join(to_run)]) + ' ' + str(variables)
	process = subprocess.Popen(run_command, stdout = subprocess.PIPE, stderr = None, shell = True).communicate()[0].decode('utf-8').split('\n')
	
	for index, line in enumerate(process):
		if line == 'True':
			process[index] = 'Sant'
		elif line == 'False':
			process[index] = 'Falskt'
	
	process = '\n'.join(process)
	print(process)


has_file = False
run_command = 'python3 run_enkelt.py '

try:
	if sys.version_info[0] < 3:
		raise Exception("Du måste använda python 3")
	else:
		sys_args = []
		
		if len(sys.argv) > 1:
			sys_args = sys.argv[1:]
		
		for arg in sys_args:
			if '.e' not in arg:
				run_command += arg + ' '
			else:
				has_file = True

		if has_file:
			data = []
			for i, arg in enumerate(sys_args):
				if '.e' in arg:
					with open(sys_args[i], 'r+') as f:
						data = f.readlines()
						break
			run_enkelt(data, {})
		else:
			if not sys_args:
				os.system('python3 run_enkelt.py')
			else:
				run_command = 'python3 run_enkelt.py '
				tmp_to_run = sys_args[0][1:-1]
				tmp_to_run = tmp_to_run.split(',')
				
				tmp_variables = sys_args[1][1:-1]
				tmp_variables = tmp_variables.split(',')
				
				run_enkelt(tmp_to_run, tmp_variables)
except Exception as e:
	print(e)
