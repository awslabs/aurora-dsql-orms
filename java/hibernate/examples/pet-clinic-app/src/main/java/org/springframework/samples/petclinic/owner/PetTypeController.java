package org.springframework.samples.petclinic.owner;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.validation.BindingResult;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;

import jakarta.validation.Valid;

@Controller
@RequestMapping("/petTypes")
public class PetTypeController {

	private final PetTypeRepository petTypeRepository;

	public PetTypeController(PetTypeRepository petTypeRepository) {
		this.petTypeRepository = petTypeRepository;
	}

	@GetMapping("/new")
	public String initCreationForm(Model model) {
		model.addAttribute("petType", new PetType());
		return "pets/createOrUpdatePetTypeForm";
	}

	@PostMapping("/new")
	public String processCreationForm(@Valid PetType petType, BindingResult result) {
		if (result.hasErrors()) {
			return "pets/createOrUpdatePetTypeForm";
		}
		else {
			this.petTypeRepository.save(petType);
			return "redirect:/owners";
		}
	}

	// Add other methods for listing, updating, and deleting pet types

}
