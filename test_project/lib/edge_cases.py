#multiline class signature
import datetime

class Lair(
        PhysicalFacility,
        Underground,
        CanHire,
        ProducesPonkeys):
    pass #Lair body starts here

#multiline function signature
def send_memo(
        from_employee,
        to_employee,
        regarding,
        body):
    '''::::send_memo body starts here'''
    return (
        "Re: " + regarding + "\n\n"
        + "Heya, {}, it's {}, from the office down the hall...\n".format(
            from_employee.first_name,
            to_employee.first_name)
        + body)


#uses dots (a 'getattr node') when specifying parent class
class WeirdSubclass(datetime.datetime):
    pass #WeirdSubclass body starts here