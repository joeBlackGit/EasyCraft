# EasyCraft
Makes setting up a Minecraft server less of a hassle.

# Getting Started
There are two ways to setup the server. The manual way has more steps, but this repo is designed to make it easier.

## The Automatic Way (Using this project)
If you have python or python3 installed, here's what you should do. 

- First, create a folder somewhere you want the server to live. (e.g. C:\Users\MinecraftServers)
- Next, clone this repository into the folder. The server will actually live inside of the downloaded folder.
- To clone the repo, either download and unzip the zip file of the repo in GitHub or open a Command Prompt and run 

``` bash
cd C:\Path\To\MineCraftServers
git clone https://github.com/joeBlackGit/EasyCraft.git
cd EasyCraft
 ```
 - Next navigate into the EasyCraft folder and run the following in the Command Prompt
``` bash
python src/setup.py
 ```

- If you get a python error, try running it as python3 src/setup.py and if that doesn't work you may need to install Python and or add it to your PATH variables (sorry not explaining that)
- If it works, you'll see the server.jar download and then you'll see some prompts to accept the EULA, Enter 'y' to accept OR type 'N' and you can navigate to wherever the eula.txt file drops (should be the root of the directory) then open it in a text editor and change
```text
 eula=false
 ```
to
 ```text
 eula=true
 ```
 - Back in the Command Prompt, once the EULA is accepted (This is something MineCraft requires you to do) then you'll see a prompt to either run the server now or not. You can run the server, or not. 
 - With this done, you will now be able to navigate to the server folder (e.g. C:\Users\MinecraftServers\EasyCraft\server) and easily start the server by double clicking the start.bat file (Windows) or the start.sh file (idk Linux or Mac probably).


## Usual Approach
The usual manual way to get the server going (without using this repo) would be as follows:
 - Navigate to https://www.minecraft.net/en-us/download/server and download the server .jar file
 - Make a folder where you want the server to exist. All data related to the world and the .jar file will go here.
 - Open the Command Prompt (Windows) and run the following code from the root of the server folder (note, if the .jar file is not called 'server.jar' you will have to change the code below to match whatever the .jar file is called)
``` bash
 java -Xms2G -Xmx4G -jar server.jar
 ```
 - The server will set up everything Minecraft needs inside the folder, but the server won't start until you accept the EULA
 - To accept the EULA, navigate to wherever the eula.txt file drops (should be the root of the directory)
 - Open it in a text editor, change the line from

 ```text
 eula=false
 ```
to
 ```text
 eula=true
 ```
 - In the Command Prompt, run the run command again:
 ``` bash
 java -Xms2G -Xmx4G -jar server.jar
 ```
 - Now the server is running. You can save the server by running 
``` bash
    save-all
 ```
or you can stop the server by running
  ``` bash
    stop
 ```
- Then whenever you want to run the server again, you run the run command.

However, your friends still can't connect to the serve just yet. For that, you will need to Port Foward you IP and, what I recommend doing, is masking your IP and use a stable domain name so you IP does not change. I use Duck.DNS for this. Regardless, whether you do that or not, this project does not help you with that. 

# Configuring the IP and Using DuckDNS (Optional)

To make it so your friends can join, you will have to add a port forwarding reservation to your router. I can't explain exactly how to do it. But for me, I have an eero, so I open the app, find Port Forward reservations, and make a reservation for port 25565.

The protocol needs to bve TCP
The external port needs to be 25565
The internal port needs to be 25565
The Internal IP needs to be your computer's LAN IP
You can add a descripotion.

People should then be able to join 

If you don't want everyone to know your IP

