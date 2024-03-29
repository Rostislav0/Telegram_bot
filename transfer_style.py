from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

import torchvision.transforms as transforms
import torchvision.models as models

import copy


class Style_Transfer(object):

    def __init__(self, path_style_image, path_content_image, num_steps_from_user):
        self.imsize = 512
        self.loader = transforms.Compose([
            transforms.Resize(self.imsize),  # нормируем размер изображения
            transforms.CenterCrop(self.imsize),
            transforms.ToTensor()])  # превращаем в удобный формат

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.style_img = self.image_loader(path_style_image)  # as well as here
        self.content_img = self.image_loader(path_content_image)  # измените путь на тот который у вас.



        self.cnn_normalization_mean = torch.tensor([0.485, 0.456, 0.406]).to(self.device)
        self.cnn_normalization_std = torch.tensor([0.229, 0.224, 0.225]).to(self.device)

        self.content_layers_default = ['conv_4']
        self.style_layers_default = ['conv_1', 'conv_2', 'conv_3', 'conv_4', 'conv_5']

        self.cnn = models.vgg19(pretrained=True).features.to(self.device).eval()

        self.num_steps_from_user = num_steps_from_user

    def image_loader(self, image_name):

        image = Image.open(image_name)
        image = self.loader(image).unsqueeze(0)
        return image.to(self.device, torch.float)

    class ContentLoss(nn.Module):

        def __init__(self, target, ):
            super(Style_Transfer.ContentLoss, self).__init__()
            # we 'detach' the target content from the tree used
            # to dynamically compute the gradient: this is a stated value,
            # not a variable. Otherwise the forward method of the criterion
            # will throw an error.
            self.target = target.detach()  # это константа. Убираем ее из дерева вычеслений
            self.loss = F.mse_loss(self.target, self.target)  # to initialize with something

        def forward(self, input):
            self.loss = F.mse_loss(input, self.target)
            return input

    def gram_matrix(self, input):
        batch_size, h, w, f_map_num = input.size()  # batch size(=1)
        # b=number of feature maps
        # (h,w)=dimensions of a feature map (N=h*w)

        features = input.view(batch_size * h, w * f_map_num)  # resise F_XL into \hat F_XL

        G = torch.mm(features, features.t())  # compute the gram product

        # we 'normalize' the values of the gram matrix
        # by dividing by the number of element in each feature maps.
        return G.div(batch_size * h * w * f_map_num)

    class StyleLoss(nn.Module):
        def __init__(self, target_feature):
            super(Style_Transfer.StyleLoss, self).__init__()
            self.target = Style_Transfer.gram_matrix(self, target_feature).detach()
            self.loss = F.mse_loss(self.target, self.target)  # to initialize with something

        def forward(self, input):
            G = Style_Transfer.gram_matrix(self, input)
            self.loss = F.mse_loss(G, self.target)
            return input

    class Normalization(nn.Module):
        def __init__(self, mean, std):
            super(Style_Transfer.Normalization, self).__init__()
            # .view the mean and std to make them [C x 1 x 1] so that they can
            # directly work with image Tensor of shape [B x C x H x W].
            # B is batch size. C is number of channels. H is height and W is width.
            self.mean = torch.tensor(mean).view(-1, 1, 1)
            self.std = torch.tensor(std).view(-1, 1, 1)

        def forward(self, img):
            # normalize img
            return (img - self.mean) / self.std

    def get_style_model_and_losses(self, normalization_mean, normalization_std):
        content_layers = self.content_layers_default
        style_layers = self.style_layers_default
        self.cnn = copy.deepcopy(models.vgg19(pretrained=True).features.to(self.device).eval())

        # normalization module
        normalization = Style_Transfer.Normalization(normalization_mean, normalization_std).to(self.device)

        # just in order to have an iterable access to or list of content/syle
        # losses
        content_losses = []
        style_losses = []

        # assuming that cnn is a nn.Sequential, so we make a new nn.Sequential
        # to put in modules that are supposed to be activated sequentially
        model = nn.Sequential(normalization)

        i = 0  # increment every time we see a conv
        for layer in self.cnn.children():
            if isinstance(layer, nn.Conv2d):
                i += 1
                name = 'conv_{}'.format(i)
            elif isinstance(layer, nn.ReLU):
                name = 'relu_{}'.format(i)
                # The in-place version doesn't play very nicely with the ContentLoss
                # and StyleLoss we insert below. So we replace with out-of-place
                # ones here.
                # Переопределим relu уровень
                layer = nn.ReLU(inplace=False)
            elif isinstance(layer, nn.MaxPool2d):
                name = 'pool_{}'.format(i)
            elif isinstance(layer, nn.BatchNorm2d):
                name = 'bn_{}'.format(i)
            else:
                raise RuntimeError('Unrecognized layer: {}'.format(layer.__class__.__name__))

            model.add_module(name, layer)

            if name in content_layers:
                # add content loss:
                target = model(self.content_img).detach()
                content_loss = Style_Transfer.ContentLoss(target)
                model.add_module("content_loss_{}".format(i), content_loss)
                content_losses.append(content_loss)

            if name in style_layers:
                # add style loss:
                target_feature = model(self.style_img).detach()
                style_loss = Style_Transfer.StyleLoss(target_feature)
                model.add_module("style_loss_{}".format(i), style_loss)
                style_losses.append(style_loss)

        # now we trim off the layers after the last content and style losses
        # выбрасываем все уровни после последенего styel loss или content loss
        for i in range(len(model) - 1, -1, -1):
            if isinstance(model[i], Style_Transfer.ContentLoss) or isinstance(model[i], Style_Transfer.StyleLoss):
                break

        model = model[:(i + 1)]

        return model, style_losses, content_losses

    def get_input_optimizer(self, input_img):
        # this line to show that input is a parameter that requires a gradient
        # добоваляет содержимое тензора катринки в список изменяемых оптимизатором параметров
        optimizer = optim.LBFGS([input_img.requires_grad_()])
        return optimizer

    def run_style_transfer(self, num_steps,
                           style_weight=100000, content_weight=1):
        """Run the style transfer."""
        print('Building the style transfer model..')
        num_steps = 10 * num_steps
        model, style_losses, content_losses = self.get_style_model_and_losses(self.cnn_normalization_mean,
                                                                              self.cnn_normalization_std)
        optimizer = self.get_input_optimizer(self.content_img)

        print('Optimizing..')
        run = [0]
        while run[0] <= num_steps:

            def closure():
                # correct the values
                # это для того, чтобы значения тензора картинки не выходили за пределы [0;1]
                self.content_img.data.clamp_(0, 1)

                optimizer.zero_grad()

                model(self.content_img)

                style_score = 0
                content_score = 0

                for sl in style_losses:
                    style_score += sl.loss
                for cl in content_losses:
                    content_score += cl.loss

                # взвешивание ощибки
                style_score *= style_weight
                content_score *= content_weight

                loss = style_score + content_score
                loss.backward()

                run[0] += 1
                if run[0] % 50 == 0:
                    print("run {}:".format(run))
                    print('Style Loss : {:4f} Content Loss: {:4f}'.format(
                        style_score.item(), content_score.item()))
                    print()

                return style_score + content_score

            optimizer.step(closure)

        # a last correction...
        self.content_img.data.clamp_(0, 1)

        return self.content_img

    def sdf(self):
        self.result = self.run_style_transfer(self.num_steps_from_user)

        unloader = transforms.ToPILImage()

        image = self.result.cpu().clone()
        image = image.squeeze(0)  # функция для отрисовки изображения
        image = unloader(image)
        return image


