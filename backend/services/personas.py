"""
Darwin Enterprise Evolve Beta — Customer Personas
20 customer personas for CID analysis across demographics, tech comfort, and priorities.
"""


class CustomerPersona:
    def __init__(self, name, age, tech_comfort, driving_frequency, vehicle_type,
                 primary_use, safety_priority, convenience_priority, aesthetics_priority,
                 budget_sensitivity, description):
        self.name = name
        self.age = age
        self.tech_comfort = tech_comfort
        self.driving_frequency = driving_frequency
        self.vehicle_type = vehicle_type
        self.primary_use = primary_use
        self.safety_priority = safety_priority
        self.convenience_priority = convenience_priority
        self.aesthetics_priority = aesthetics_priority
        self.budget_sensitivity = budget_sensitivity
        self.description = description

    def to_dict(self):
        return {
            "name": self.name,
            "age": self.age,
            "tech_comfort": self.tech_comfort,
            "driving_frequency": self.driving_frequency,
            "vehicle_type": self.vehicle_type,
            "primary_use": self.primary_use,
            "safety_priority": self.safety_priority,
            "convenience_priority": self.convenience_priority,
            "aesthetics_priority": self.aesthetics_priority,
            "budget_sensitivity": self.budget_sensitivity,
            "description": self.description,
        }


CUSTOMERS = [
    CustomerPersona("Tech-Savvy Commuter", 28, 9, "daily", "sedan", "commute", 6, 9, 7, "medium",
                     "Young professional who embraces new technology and wants seamless connectivity"),
    CustomerPersona("Safety-First Parent", 42, 5, "daily", "SUV", "family", 10, 6, 3, "low",
                     "Parent prioritizing family safety over flashy features"),
    CustomerPersona("Minimalist Senior", 61, 3, "weekly", "sedan", "errands", 8, 4, 2, "high",
                     "Prefers simple, reliable interfaces without complexity"),
    CustomerPersona("Performance Enthusiast", 35, 8, "daily", "sports", "recreation", 5, 7, 9, "low",
                     "Values cutting-edge tech and sleek design for driving enjoyment"),
    CustomerPersona("Budget-Conscious Student", 22, 7, "occasional", "compact", "school", 6, 8, 5, "high",
                     "Wants modern features but is very price-sensitive"),
    CustomerPersona("Luxury Professional", 45, 6, "daily", "luxury", "business", 7, 8, 8, "low",
                     "Expects premium experience with sophisticated but intuitive interfaces"),
    CustomerPersona("Practical Family Driver", 38, 5, "daily", "SUV", "family", 8, 7, 4, "medium",
                     "Needs reliable, family-friendly features without unnecessary complexity"),
    CustomerPersona("Tech-Averse Traditional", 55, 2, "weekly", "truck", "work", 9, 3, 2, "medium",
                     "Strongly prefers physical controls and traditional interfaces"),
    CustomerPersona("Early Adopter Millennial", 31, 10, "daily", "electric", "lifestyle", 5, 9, 8, "medium",
                     "Loves cutting-edge technology and customization options"),
    CustomerPersona("Outdoor Adventure Driver", 29, 6, "weekend", "SUV", "recreation", 7, 6, 6, "medium",
                     "Needs rugged, reliable systems for outdoor adventures"),
    CustomerPersona("Ride-Share Driver", 34, 8, "daily", "hybrid", "work", 8, 10, 4, "high",
                     "Professional driver needing efficient, intuitive controls for productivity and passenger safety"),
    CustomerPersona("Vision-Impaired Senior", 68, 2, "weekly", "sedan", "medical", 10, 5, 1, "medium",
                     "Requires large text, high contrast, and audio feedback for accessibility"),
    CustomerPersona("New Teen Driver", 17, 9, "occasional", "compact", "school", 4, 8, 9, "high",
                     "Digital native who wants Instagram-worthy tech but lacks driving experience"),
    CustomerPersona("Fleet Manager", 41, 6, "daily", "commercial", "business", 9, 8, 2, "high",
                     "Needs standardized, durable interfaces that minimize driver training and maintenance costs"),
    CustomerPersona("Arthritic Retiree", 72, 1, "weekly", "SUV", "errands", 9, 6, 2, "medium",
                     "Limited hand mobility requires large, physical buttons that are easy to press"),
    CustomerPersona("Busy Executive", 52, 7, "daily", "luxury", "business", 6, 10, 7, "low",
                     "Needs hands-free operation and voice commands for multitasking while driving"),
    CustomerPersona("Single Parent Nurse", 36, 4, "daily", "minivan", "family", 10, 8, 3, "high",
                     "Works long shifts, needs simple, fatigue-friendly controls for safe family transport"),
    CustomerPersona("Small Business Owner", 44, 5, "daily", "pickup", "work", 7, 9, 4, "medium",
                     "Values durability and functionality over fancy features for work vehicle"),
    CustomerPersona("International Exchange Student", 20, 8, "occasional", "used", "school", 6, 7, 6, "high",
                     "Unfamiliar with American driving norms, needs intuitive, universally understood interfaces"),
    CustomerPersona("Delivery Driver", 26, 7, "daily", "van", "work", 8, 10, 2, "medium",
                     "Makes 50+ stops daily, needs lightning-fast, one-handed operation while managing packages"),
]
