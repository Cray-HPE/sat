# API Requests in SAT

Many ``sat`` subcommands make requests to the various Shasta system management
services' APIs. The ``sat.apiclient`` and ``sat.session`` modules provide an
easy way to make authenticated requests to those APIs through the API gateway.

These modules will take care of looking at the config file, finding the hostname
of the API gateway, finding the configured user name, loading the token file for
that user, and then passing along the token in the header of the request.

## Example API Request

Here is an example of code that will make requests to a new API named ``foo``
whose URL begins with ``foo/`` under the API gateway.

First we define a new client class in the ``sat.apiclient`` module. This one
uses the v1 API of the foo service:

    class FooClient(APIGatewayClient):
        base_resource_path = 'foo/v1'

To use this client in our code, we create an instance of this ``FooClient``
class and pass it a ``SATSession`` instantiated with no args as follows:

    from sat.apiclient import FooClient
    from sat.session import SATSession
    
    ...
    
    foo_client = FooClient(SATSession())

Then we can make an HTTP GET, POST, PUT, or DELETE request to the foo API using
the corresponding ``get``, ``post``, ``put``, or ``delete`` methods of our
``foo_client``. For example, to GET all the foo items with a ``type`` query
parameter:

    response = foo_client.get('items', {'type': 'just_right'})

This will return the ``Response`` object from the `requests` library. We can
then call `json` on it to decode the JSON. For example:

    type_objects = response.json() 

The ``get``, ``post``, ``put``, and ``delete`` methods mentioned above support
specifying the components of the URL separately, and they will be joined with a
``/`` between each one. For example, if we want to get the details of a specific
item named ``door`` by making a HTTP GET request to `/items/door`, we could do
this:

    door_response = foo_client.get('items', 'door')

or this:

    door_response = foo_client.get('items/door')

So far, this is a pretty thin wrapper around the ``requests`` library, and the
main benefit is that it loads config file options that affect requests to the
API gateway and handles authentication accordingly. However, it is also possible
to define additional methods on the individual ``APIGatewayClient`` classes that
wrap requests to the API for that service and make them easier to use. For
example, maybe we want to create a method that creates a new item in the foo
service with a given name and a location. We can do so as follows: 

    class FooClient(APIGatewayClient):
        base_resource_path = 'foo/v1'
        
        def create_item(self, name, location=DEFAULT_LOCATION):
            """Create a foo item with the given name and location.
    
            Args:
                name (str): the name of the item
                location (str): the location of the item
    
            Returns:
                The response from the POST to 'items'.
    
            Raises:
                APIError: if the POST request to create the item fails.
            """
            request_body = {
                'name': name,
                'location': location
            }
            return self.post('items', json=request_body)
