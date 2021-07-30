from tkinter import *
master = Tk() 
master.title("IDT - ICE")
master.geometry("500x500")


Label(master, text='Bucket Name').grid(row=2) 
e1 = Entry(master) 
e1.grid(row=2, column=1) 

button = Button(master, text='Setup Stack', width=25, command=master.destroy).grid(row=4, column=1) 
button = Button(master, text='Terminate Stack', width=25, command=master.destroy).grid(row=5, column=1) 



mainloop() 