// Execute when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {

    // Create the websocket (real-time connection between server and client)
    var socket = io.connect('http://' + document.domain + ':' + location.port);
    // Grab the user's local storage
    var my_storage = window.localStorage;
    // Execute when the user connects to the websocket
    socket.on('connect', () => {
        // If the user was in a room before they left send them back to that room
        if (my_storage.getItem('channel')) {

            socket.emit("join_channel", my_storage.getItem('channel'));
        }
        else {
            document.querySelector("#chat").style.display = "none";
        }
        // If the user has not added enable the starter form and disable channel forms
        if(!my_storage.getItem('username')) {
            document.querySelector("#create_button").disabled = true;
            document.querySelector("#channel_list").style.display = "none";
        }
        // If the user added a name disable the starter form and enable the channel forms
        else {
            document.querySelector("#create_button").disabled = false;
            document.querySelector("#channel_list").style.display = "block";
            // save the username on the server side
            socket.emit("username", my_storage.getItem("username"));
        }

    });

    // Execute when the user joins a channel
    socket.on('join_channel', data => {
        // Save the channel in the client's memory for later use
        my_storage.setItem('channel', data["channel"]);
        // Clear the messages area
        document.querySelector("#messages").innerHTML = "";
        // Use the channel as the chat's header
        document.querySelector("#chathead").innerHTML = data["channel"];
        // Take the user to the room
        document.querySelector("#chat").style.display = "block";
        // Fill up the messages area with the channel's messages
        var x;
        for (x in data["messages"]) {
            const li = document.createElement('li');
            li.innerHTML = `<strong>${data["messages"][x].user}:</strong> <div><span>${data["messages"][x].msg}</span></div> <small>(${data["messages"][x].my_time})</small>`;
            document.querySelector("#messages").append(li);
        }
    });
    // Execute when the user leaves a channel
    socket.on('leave_channel', channel => {
        my_storage.removeItem("channel");
        //hide the chat and reset its header
        document.querySelector("#chathead").innerHTML = "";
        document.querySelector("#chat").style.display = "none";
    });
    // Execute when there was an error while creating a channel
    socket.on('channel_error', msg => {
        // Notify the user about the error
        alert(msg);
    });

    // Execute when a message is sent
    socket.on('room_message', data => {
        console.log("Message received!");
        // Show message for all users on the channel
        const li = document.createElement('li');
        li.innerHTML = `<strong>${data.user}:</strong> <div><span>${data.msg}</span></div> <small>(${data.my_time})</small>`;
        document.querySelector("#messages").append(li);
    });

    // Execute when the send button is clicked
    document.querySelector("#sendbutton").onclick = () => {
        // Send a JSON to the server with the channel, the message and the user's name in it
        msg = document.querySelector("#my_message").value;
        user = my_storage.getItem('username');
        const channel = my_storage.getItem('channel');
        socket.emit('room_message',{'msg': msg, 'user': user, 'channel': channel});
        document.querySelector("#my_message").value = '';
    };
    // Execute when the leave channel button is clicked
    document.querySelector("#leave_channel").onclick = () => {
        // Trigger the leave channel event on the server side
        socket.emit("leave_channel", my_storage.getItem("channel"));
    };
    // Execute when an element of the channel list is clicked
    document.querySelectorAll(".my_channel").forEach(li => {
        li.onclick = () => {
            // Trigger the change channel event on the server side
            socket.emit('change_channel', my_storage.getItem('channel'), li.dataset.channel);
        };
    });

    // Execute when the starter form is submitted
    document.querySelector("#starter_form").onsubmit =  () => {
        // Save the username in the local storage
        my_storage.setItem('username', document.querySelector("#name").value);
        // Enable the channel creation/selection
        document.querySelector("#create_button").disabled = false;
        document.querySelector("#channel_list").style.display = "block";
        // Reset the form's value
        document.querySelector("#name").value = "";
        socket.emit("username", my_storage.getItem('username'));
        // Prevent form submission
        return false;

    };
    // Execute when the create channel form is submitted
    document.querySelector("#create_channel").onsubmit = () => {
        // Emit the channel creation event using the input from the user
        const channel = document.querySelector("#channel").value;
        socket.emit("channel_creation", channel);
        // Prevent form submission
        return false;
    };


});
