from tkinter import *
import tkinter.scrolledtext as tkst
from tkinter import ttk
import sys
import threading
import os
import subprocess
import shutil
from tkinter.filedialog import askopenfilename
import time



class CoreGUI(object):
    def __init__(self,parent):
        self.parent = parent
        self.start_progress_bar = 0
        self.invalid_bucket = 0
        self.InitUI()
        self.bucket_name = ""
        self.credential_path = ""
        self.parent.title("ICE Setup V 0.9")

        Label(self.parent, text="Progress").grid(column=0, row=1, columnspan=1)
        self.progress = ttk.Progressbar(self.parent, orient="horizontal",length=100, mode="determinate")
        self.progress.grid(row=1,column=1)
        self.progress["maximum"] = 5

        Label(self.parent, text="Bucket Name :").grid(column=2, row=1, columnspan=1)
        self.bucket = Entry(self.parent)
        self.bucket.grid(column=3, row=1, columnspan=1)

        button = Button(self.parent, text="Select credential", command=self.select_credential)
        button.grid(column=4, row=1, columnspan=1)

        
        button = Button(self.parent, text="Create ICE", command=self.runProcess)
        button.grid(column=5, row=1, columnspan=1)

        button = Button(self.parent, text="Clean up ICE", command=self.terminate)
        button.grid(column=6, row=1, columnspan=1)

        if(os.path.isfile('log.txt')):
            shutil.move("log.txt", "log.txt.bck")
        shutil.copyfile("log_template.txt", "log.txt")
        self.parent.iconbitmap(r'renesas_icon_1.ico')
        self.update()


    def runProcess(self): 
        self.progress["maximum"] = 80  
        self.progress["value"] = 0
        self.start_progress_bar = 1 
        self.bucket_name = self.bucket.get()
        print("bucket name "+ self.bucket_name)
        p = subprocess.Popen(['streetLampAutomation.exe' , self.bucket_name,self.credential_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # while(True):
        #     # returns None while subprocess is running
        #     retcode = p.poll() 
        #     line = p.stdout.readline()
        #     yield line
        #     if retcode is not None:
        #         break

    def terminate(self):
        print("terminating the stack")
        self.progress["maximum"] = 2  
        self.progress["value"] = 0
        self.start_progress_bar = 1
        self.bucket_name = self.bucket.get() 
        p = subprocess.Popen(['terminationStack.exe' , self.bucket_name,self.credential_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def select_credential(self):
        filename = askopenfilename()
        self.credential_path = filename
        print("selected the credential file "+filename)
        #p = subprocess.Popen(['python','my_logger.py' , "Selected the credential file"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p = subprocess.Popen(['my_logger.exe' , "User credential file :" ,filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        #p = subprocess.Popen(['python','terminationStack.py' , 'kbilgund-test'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def main(self):
        self.text_box.insert(INSERT, "\n")
        self.text_box.insert(END,"Creating the stack".rstrip())
        self.parent.update()
        for line in self.runProcess():
            if(line != b''):
                self.text_box.insert(INSERT, "\n")
                self.text_box.insert(END,line.rstrip())
                #self.parent.update()
                print (line)




    def InitUI(self):
        self.text_box = tkst.ScrolledText(self.parent, wrap='word', height = 15, width=100)
        self.text_box.grid(column=0, row=0, columnspan = 15, sticky='NSWE', padx=10, pady=10)



#        sys.stdout = StdoutRedirector(self.text_box)


    

    def update(self):
        with open("log.txt","r") as f:
            data = f.read()
            #print(data.count("finished"))
            self.text_box.delete("1.0", "end")  # if you want to remove the old data
            if(self.invalid_bucket==0):
                self.text_box.insert(END,data)
            else:
                self.text_box.insert(END,"Enter Valid bucket name")

            self.text_box.see("end")
            #if(self.start_progress_bar == 1):
            #    self.progress["value"] = data.count("finished")

            #print(data)
            if(data.count("waiting for stack to be ready...")==1 and data.count("finished stack creation")==0):
                #print("inside 1st if")
                if(self.progress["value"] < 75):
                    self.progress["value"] += 1
            elif(data.count("finished stack creation")==1):
                #print("inside 2nd if")
                self.progress["value"] = 76+data.count("finished")
            else:
                #print("inside 3rd if")
                self.progress["value"] = data.count("finished")

                

        self.text_box.after(3000, self.update)





#print("test 1")
root = Tk()
gui = CoreGUI(root)
root.mainloop()