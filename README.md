# NoPE 

## A Python wrapper for the Library

Please visit our [Docu](https://zema-ggmbh.github.io/NoPE-Docs/)

## Show me `NoPE` in 5 Minutes! 

### 1. Create a `Nodejs` Project

Get started by **creating a new project** distributed using `NoPE`.

For our **PYTHON** project we will use the nope-js-node cli tools to create a Project.

1. Installation using  npm:
  ```bash
  npm install -g nope-js-node
  ```
2. Start your first Project:
  ```bash
  nope-js project create
  ```
  This should open a `cli`.

3. Answer the requried questions to complete create the directory.
  - Name the project `HelloWorld`
  - Give it a short summary. This summary will used during distributing your project.
  - make shure you select `python` as project type    

4. navigate to the create folder ( e.g. `cd ./HelloWorld` ) 

  This creates a project structure.

5. Open your IDE (e.g. vscode)

By using the project-tool the following features are added to the project:
- Debugging of the application using VS code (launch-file)
- Creation of a doc file (see doc/make)
- Helpers to build a browser related version
- Use of a changelog
- Deployment as a package
- Simple extension using project-tool

## 2. Add a Service in `Python`

Our goal is to define a greeting service
> The service creates a greeting message for a person. 

### Why a Service

> This service is independent of how many times it has been called.
> Our functionality is stateless, this allows us to use a service.

### Using the `CLI` to generate the Service

1. To create the Service: 
  use the `project-tool` to create the service 

  ```bash
  nope-js project edit
  ```

2. Perfom the following selection inside of the tool.
  1. Selection `add`, to add a new element
  2. Select `service`, because we want to create a service
  3. Enter the name of the service, in our case `HelloWorld`
  
  Creation of the corresponding files and imports is done automatically

  This will update our project folder.

Now `NoPE` defined a new service file (`HelloWorldFunctions.py`) for us:

```python
#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from nope import getNopeLogger

LOGGER = getNopeLogger("HelloWorldService")

# Please provide the schema for the Function.
# See the Example below.
SCHEMA = {
    "type": "function",
        
    # To describe the used inputs of a function or serive we added the field "inputs" to the schema.
    # It contains a list of all required inputs.
    "inputs": [
    ],
    # To describe the return of a function we added the field "outputs". It contains a 
    # JSON-Schema Object.
    "outputs":{
    }
}

async def HelloWorld(greetings: str):
    # Please overwrite me!
    LOGGER.debug("calling service 'HelloWorld' with the following parameters:" + str(greetings))
    return "Hello " + greetings + "!"
```

In that file, you will find a template for the service we want to implement. By default, the newly created service implements the hello-world behavior. This must changed. In our case it matches the desired behavior.


> All services **must** be implemented `async` manner. This is necessary so that the runtime is not blocked.


### Adding a Service interface

We now want to describe our service, that it can be used correctly at different Runtimes. Therefore we will define the `schema` to the `SCHEMA` variable. This Schema follows the definition of a `JSON-Schema`:

```python
SCHEMA = {
    "type": "function",
        
    # To describe the used inputs of a function or serive we added the field "inputs" to the schema.
    # It contains a list of all required inputs.
    "inputs": [
        {
            # The Description of the Parameter
            "description": "The name which should receive a Greeting",
            # Its used name in the function (see the arguments of the function)
            "name": "greetings",
            # The Schema follows a default JSON-Schema
            "schema": {
                "type": "string"
            }
        }
    ],
    # To describe the return of a function we added the field "outputs". It contains a 
    # JSON-Schema Object.
    "outputs":{
        "type": "string",

        # We provide some extra Info for the other users.
        "description": "The greeting Message!"
    }
}
```

Because the python implementation is lacking some typings please checkout the docs

## 3. Running the Service:

To run the `service` and distribute to different `NoPE`-Runtimes we have to determine a configuration:

```bash
nope-py scan
```
The `cli` will find all defined `services` or `modules` exposed in a so called `NoPE-Package` (This has been created automatically during the initalization of the project). The tool will store its results in the following configuration (located at `./config/config.json`):

```json
[
    {
        "nameOfPackage": "HelloWorld",
        "autostart": {},
        "defaultInstances": [],
        "providedServices": [
            {
                "options": {
                    "schema": {
                        ...
                    },
                    "resultSink": null,
                    "timeout": -1,
                    "id": "HelloWorld",
                    "ui": {
                        "file": false,
                        "autoGenBySchema": false,
                        "requiredProvidersForRendering": []
                    },
                    "isDynamic": false
                }
            }
        ],
        "providedClasses": [],
        "requiredPackages": [],
        "path": "C:\\Users\\m.karkowski\\Documents\\00-Repos\\TEST\\HelloWorld\\HelloWorld\\__init__.py"
    }
]
```

Finally we are ready to distribute our service by using the command:

```bash
nope-py run
```

This will start a runtime providing our service.

## 4. Interact with the Runtime

Currently our service is only run internally (nope is not connected and runs without an external connection layer). To check and play with the distribution, we kill our old process (`ctrl+c`) create a separate process (e.g. a bash) and provide a serve:

```bash
nope-js run -c io-server
```

This will spool up a `socket-io` server on our localhost. 

Afterwards we will restart our Runtime hosting the created service using `io-sockets` as connection layer:

```bash
nope-py run -c io-client
```

Now we are able to start our `interact-tool` to manually execute our process:

```bash
nope-js interact -c io-client -s
```

To use the `interact`-**tool** follow the questions:

1. What do you want to do?
    - We want to inspect our distributed system -> `inspect`
2. What do you want to inspect?
    - We want to check if our service is present -> `service`
    - We should be albe to see our `HelloWorld`-Service (see 1)
3. Now we want to execute this service. Therefore we navigate `back` to the main menu
4. Now we select `execute` and afterwards `service` because we want to execute our service
5. Now the Tool renders the available services and we select `HelloWorld` (see 2) and it will render the previously defined Schema.
6. Now we have to enter the inputs required by the Service:
    - It is important that the parameters are entered as list (because there might be more the 1 Parameter)
    - Enter the parameters as valid `JSON` Data.
    - Press `enter`

    > Executing services with the interact tool will perfom function immedialty. If you integrated Hardware be aware of that.

7. The Tool shows the result (see 4)


> You are now running a distributed System using **remote procedure calls** in ***python***