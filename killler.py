import os
import signal


def kill_hidden_process():
    # Running the aforementioned command and saving its output
    output = os.popen('wmic process get description, processid').read()
    process_list = output.split('\n\n')[2:]
    processes = {}
    for process in process_list:
        try:
            *name, pid = process.split()
            name = ' '.join(name)
            processes[name] = int(pid)
        except ValueError:
            ...

    # Searching hidden python process and kill it
    try:
        os.kill(processes['pythonw.exe'], signal.SIGTERM)
        print('Hidden process was found and terminated')
    except KeyError:
        ...


if __name__ == '__main__':
    kill_hidden_process()
