# sbhum

## switchbot temp sensor controlling a kasa smart plug (for a humidifier application)

Much like the jcostom/sbtemp app, this uses a Switchbot Meter to read environmental conditions in an area and control a Kasa smart plug. This time, instead of caring about temperature, we care about humidity. Also, instead of running a small space heater, we're running a humidifier. Our goal is to maintain a certain minimum level of humidity within this space (ie not too dry). 

The other key difference in this app is the added element of minimum run-time - once we switch into the run-state, we want to run the humidifier for a minimum amount of time, to avoid fast on-off cycling, which is hard on the humidifier unit. After all, we don't want to kill the thing, right?

Like before, this thing pushes data into the same InfluxDB 2.x instance we're using with our jcostom/sbtemp container. Just another set of measurements in the data bucket. So, I'll include that example config in the repo here as well. Again, I'm using the Influx 2.x API, so if you're trying to use Influx 1.x and wondering why this isn't working, you've got your answer.

Lastly, once again, I'm including a sample docker-compose file, suitable for launching this, or using in Portainer. Use it as you wish, or don't. You do you.
